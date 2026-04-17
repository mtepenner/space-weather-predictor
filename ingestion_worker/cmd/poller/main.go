package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mtepenner/space-weather-predictor/ingestion_worker/internal/publisher"
	"github.com/mtepenner/space-weather-predictor/ingestion_worker/internal/swpc_client"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://postgres:password@localhost:5432/spaceweather?sslmode=disable"
	}

	writer, err := publisher.NewDBWriter(dsn)
	if err != nil {
		slog.Error("failed to connect to database", "error", err)
		os.Exit(1)
	}
	defer writer.Close()

	if err := writer.Migrate(); err != nil {
		slog.Error("failed to run database migrations", "error", err)
		os.Exit(1)
	}

	xrayClient := swpc_client.NewXRayFluxClient()
	geoClient := swpc_client.NewGeomagneticClient()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	slog.Info("ingestion worker started", "interval", "5m")

	// Run immediately on startup
	poll(ctx, xrayClient, geoClient, writer)

	for {
		select {
		case <-ticker.C:
			poll(ctx, xrayClient, geoClient, writer)
		case sig := <-sigCh:
			slog.Info("received signal, shutting down", "signal", sig)
			return
		case <-ctx.Done():
			return
		}
	}
}

func poll(ctx context.Context, xrayClient *swpc_client.XRayFluxClient, geoClient *swpc_client.GeomagneticClient, writer *publisher.DBWriter) {
	slog.Info("starting poll cycle")

	xrayReadings, err := xrayClient.Fetch(ctx)
	if err != nil {
		slog.Error("failed to fetch X-ray flux data", "error", err)
	} else {
		if err := writer.WriteXRayFlux(ctx, xrayReadings); err != nil {
			slog.Error("failed to write X-ray flux data", "error", err)
		} else {
			slog.Info("wrote X-ray flux readings", "count", len(xrayReadings))
		}
	}

	geoReadings, err := geoClient.Fetch(ctx)
	if err != nil {
		slog.Error("failed to fetch geomagnetic data", "error", err)
	} else {
		if err := writer.WriteGeomagnetic(ctx, geoReadings); err != nil {
			slog.Error("failed to write geomagnetic data", "error", err)
		} else {
			slog.Info("wrote geomagnetic readings", "count", len(geoReadings))
		}
	}

	slog.Info("poll cycle complete")
}
