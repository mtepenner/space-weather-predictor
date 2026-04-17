package publisher

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"

	_ "github.com/lib/pq"
	"github.com/mtepenner/space-weather-predictor/ingestion_worker/internal/swpc_client"
)

// DBWriter handles writing space weather data to TimescaleDB.
type DBWriter struct {
	db *sql.DB
}

// NewDBWriter creates a new DBWriter and verifies connectivity.
func NewDBWriter(dsn string) (*DBWriter, error) {
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, fmt.Errorf("opening database connection: %w", err)
	}
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("pinging database: %w", err)
	}
	slog.Info("database connection established")
	return &DBWriter{db: db}, nil
}

// Close closes the underlying database connection pool.
func (w *DBWriter) Close() error {
	return w.db.Close()
}

// Migrate creates the required hypertables if they don't exist.
func (w *DBWriter) Migrate() error {
	migrations := []string{
		`CREATE TABLE IF NOT EXISTS xray_flux (
			time        TIMESTAMPTZ NOT NULL,
			satellite   INT         NOT NULL,
			current_int  DOUBLE PRECISION,
			current_ratio DOUBLE PRECISION,
			current_flux  DOUBLE PRECISION,
			energy      TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS geomagnetic_readings (
			time       TIMESTAMPTZ NOT NULL,
			kp_index   DOUBLE PRECISION NOT NULL,
			observed   TEXT,
			noaa_scale TEXT
		)`,
		// Attempt to create TimescaleDB hypertables; ignore errors if extension unavailable.
		`DO $$ BEGIN
			IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
				PERFORM create_hypertable('xray_flux', 'time', if_not_exists => TRUE);
				PERFORM create_hypertable('geomagnetic_readings', 'time', if_not_exists => TRUE);
			END IF;
		END $$`,
	}

	for _, m := range migrations {
		if _, err := w.db.Exec(m); err != nil {
			return fmt.Errorf("running migration: %w\nSQL: %s", err, m)
		}
	}
	slog.Info("database migrations complete")
	return nil
}

// WriteXRayFlux inserts X-ray flux readings into the database using a bulk copy.
func (w *DBWriter) WriteXRayFlux(ctx context.Context, readings []swpc_client.XRayFluxReading) error {
	if len(readings) == 0 {
		return nil
	}

	tx, err := w.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("beginning transaction: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck

	stmt, err := tx.PrepareContext(ctx, `
		INSERT INTO xray_flux (time, satellite, current_int, current_ratio, current_flux, energy)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT DO NOTHING
	`)
	if err != nil {
		return fmt.Errorf("preparing statement: %w", err)
	}
	defer stmt.Close()

	for _, r := range readings {
		if _, err := stmt.ExecContext(ctx, r.TimeTag, r.Satellite, r.CurrentInt, r.CurrentRatio, r.CurrentFlux, r.Energy); err != nil {
			return fmt.Errorf("inserting X-ray flux record: %w", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("committing transaction: %w", err)
	}
	return nil
}

// WriteGeomagnetic inserts geomagnetic Kp-index readings into the database.
func (w *DBWriter) WriteGeomagnetic(ctx context.Context, readings []swpc_client.GeomagneticReading) error {
	if len(readings) == 0 {
		return nil
	}

	tx, err := w.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("beginning transaction: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck

	stmt, err := tx.PrepareContext(ctx, `
		INSERT INTO geomagnetic_readings (time, kp_index, observed, noaa_scale)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT DO NOTHING
	`)
	if err != nil {
		return fmt.Errorf("preparing statement: %w", err)
	}
	defer stmt.Close()

	for _, r := range readings {
		if _, err := stmt.ExecContext(ctx, r.TimeTag, r.KpIndex, r.Observed, r.NoaaScale); err != nil {
			return fmt.Errorf("inserting geomagnetic record: %w", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("committing transaction: %w", err)
	}
	return nil
}
