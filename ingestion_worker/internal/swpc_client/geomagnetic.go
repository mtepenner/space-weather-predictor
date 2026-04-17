package swpc_client

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"time"
)

const geomagneticURL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"

// GeomagneticReading represents a single planetary Kp-index reading.
type GeomagneticReading struct {
	TimeTag    time.Time
	KpIndex    float64
	Observed   string
	NoaaScale  string
}

// GeomagneticClient fetches planetary Kp-index data from NOAA/SWPC.
type GeomagneticClient struct {
	httpClient *http.Client
}

// NewGeomagneticClient creates a new GeomagneticClient with a default timeout.
func NewGeomagneticClient() *GeomagneticClient {
	return &GeomagneticClient{
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

// Fetch retrieves the latest Kp-index readings from NOAA.
// The API returns a JSON array of arrays: [time_tag, kp_index, observed, noaa_scale].
func (c *GeomagneticClient) Fetch(ctx context.Context) ([]GeomagneticReading, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, geomagneticURL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "space-weather-predictor/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetching geomagnetic data: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	// The API returns a 2D array where the first row is headers.
	var raw [][]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&raw); err != nil {
		return nil, fmt.Errorf("decoding geomagnetic response: %w", err)
	}

	if len(raw) < 2 {
		return nil, fmt.Errorf("unexpected response format: too few rows")
	}

	// Skip header row (index 0)
	readings := make([]GeomagneticReading, 0, len(raw)-1)
	for _, row := range raw[1:] {
		if len(row) < 4 {
			slog.Warn("skipping malformed row", "row", row)
			continue
		}

		timeStr, ok := row[0].(string)
		if !ok {
			continue
		}
		t, err := time.Parse("2006-01-02 15:04:05.000", timeStr)
		if err != nil {
			// Try alternate format
			t, err = time.Parse("2006-01-02 15:04:05", timeStr)
			if err != nil {
				slog.Warn("failed to parse time tag, skipping record", "time_tag", timeStr, "error", err)
				continue
			}
		}

		kpStr, ok := row[1].(string)
		if !ok {
			continue
		}
		kp, err := strconv.ParseFloat(kpStr, 64)
		if err != nil {
			slog.Warn("failed to parse Kp index, skipping record", "kp", kpStr, "error", err)
			continue
		}

		observed, _ := row[2].(string)
		noaaScale, _ := row[3].(string)

		readings = append(readings, GeomagneticReading{
			TimeTag:   t,
			KpIndex:   kp,
			Observed:  observed,
			NoaaScale: noaaScale,
		})
	}

	slog.Info("fetched geomagnetic data", "records", len(readings))
	return readings, nil
}
