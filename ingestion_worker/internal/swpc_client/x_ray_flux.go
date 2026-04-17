package swpc_client

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"time"
)

const xrayFluxURL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"

// XRayFluxReading represents a single X-ray flux measurement from a GOES satellite.
type XRayFluxReading struct {
	TimeTag    time.Time
	Satellite  int
	CurrentInt float64 // short wavelength 0.05-0.4 nm
	CurrentRatio float64
	CurrentFlux  float64 // long wavelength 0.1-0.8 nm
	Energy     string
}

type xrayFluxRaw struct {
	TimeTag      string  `json:"time_tag"`
	Satellite    int     `json:"satellite"`
	CurrentInt   float64 `json:"current_int"`
	CurrentRatio float64 `json:"current_ratio"`
	CurrentFlux  float64 `json:"current_flux"`
	Energy       string  `json:"energy"`
}

// XRayFluxClient fetches GOES X-ray flux data from NOAA/SWPC.
type XRayFluxClient struct {
	httpClient *http.Client
}

// NewXRayFluxClient creates a new XRayFluxClient with a default timeout.
func NewXRayFluxClient() *XRayFluxClient {
	return &XRayFluxClient{
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

// Fetch retrieves the latest X-ray flux readings from NOAA.
func (c *XRayFluxClient) Fetch(ctx context.Context) ([]XRayFluxReading, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, xrayFluxURL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "space-weather-predictor/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetching X-ray flux: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var raw []xrayFluxRaw
	if err := json.NewDecoder(resp.Body).Decode(&raw); err != nil {
		return nil, fmt.Errorf("decoding X-ray flux response: %w", err)
	}

	readings := make([]XRayFluxReading, 0, len(raw))
	for _, r := range raw {
		t, err := time.Parse("2006-01-02T15:04:05Z", r.TimeTag)
		if err != nil {
			slog.Warn("failed to parse time tag, skipping record", "time_tag", r.TimeTag, "error", err)
			continue
		}
		readings = append(readings, XRayFluxReading{
			TimeTag:      t,
			Satellite:    r.Satellite,
			CurrentInt:   r.CurrentInt,
			CurrentRatio: r.CurrentRatio,
			CurrentFlux:  r.CurrentFlux,
			Energy:       r.Energy,
		})
	}

	slog.Info("fetched X-ray flux data", "records", len(readings))
	return readings, nil
}
