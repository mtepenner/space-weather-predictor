# ☀️ Space Weather Predictor

A comprehensive simulation and forecasting platform designed to predict space weather impacts on satellite orbital decay. The system polls live data from NOAA/SWPC, processes the atmospheric physics and drag calculations, and visualizes the cascading effects on orbital trajectories through an interactive 3D dashboard.

## 📑 Table of Contents
- [Features](#-features)
- [Architecture](#-architecture)
- [Technologies Used](#-technologies-used)
- [Installation](#-installation)
- [Usage](#-usage)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Features
* **Live SWPC Ingestion:** A high-reliability Go worker polls NOAA/SWPC for solar flares (GOES X-ray flux) and geomagnetic storms (Kp-Index).
* **Atmospheric Density Modeling:** Interfaces with the standard NRLMSISE-00 atmospheric density model via a Python/FastAPI backend.
* **Orbital Decay Prediction:** Calculates drag forces (`Fd = 0.5 * rho * v^2 * Cd * A`) and numerically integrates them over time using SGP4 to predict 7-day altitude loss.
* **Dynamic 3D Dashboard:** A React/TypeScript command center featuring a WebGL visualizer of the "swelling" Earth atmosphere.
* **Fleet Alerts:** Provides real-time warnings for satellites entering critical drag regimes.
* **Persistent Storage:** Standardizes and writes incoming space weather and density logs to TimescaleDB.

## 🏗️ Architecture
The platform is built on a microservice architecture for high availability and performance:
1. **Ingestion Worker (Go):** A minimal, cron-like poller executing at set intervals to fetch satellite data and write it to the time-series database.
2. **Physics Engine (Python):** The core calculation brain exposing a FastAPI endpoint for orbital decay prediction.
3. **Space Dashboard (React/TypeScript):** The frontend UI that visualizes F10.7 flux, Kp Index, and live fleet data.
4. **Infrastructure:** Supported by TimescaleDB and orchestrated via Kubernetes manifests and Docker Compose.

## 🛠️ Technologies Used
* **Data Ingestion:** Go (Golang)
* **Physics & Simulation:** Python, FastAPI, NumPy, SciPy, PyMSIS, SGP4
* **Frontend UI:** React, TypeScript, Three.js, Recharts
* **Database & Deployment:** TimescaleDB, Docker, Kubernetes

## 💻 Installation

### Prerequisites
* Docker and Docker Compose installed.
* Ensure you have `make` installed for running build scripts and database migrations.

### Setup Steps
1. Clone the repository:
   ```bash
   git clone [https://github.com/yourusername/space-weather-predictor.git](https://github.com/yourusername/space-weather-predictor.git)
   cd space-weather-predictor
   ```
2. Run any necessary database migrations using the provided Makefile:
   ```bash
   make migrate
   ```
3. Boot up the Go poller, Python physics engine, and React UI locally using Docker Compose:
   ```bash
   docker-compose up --build -d
   ```

## 🎮 Usage
Once the services are active and the ingestion worker has polled initial data:
1. Navigate to the Space Weather Command Center in your browser (typically `http://localhost:3000`).
2. Interact with the **EarthAtmosphere3D** visualizer to see how the atmosphere swells during periods of high solar activity.
3. Monitor the **SolarWindCharts** for historical and real-time time-series data of the F10.7 flux and Kp Index.
4. Query the **DecayPredictor** for a specific satellite to view a plotted graph of its expected altitude loss over the next 7 days.
5. Keep an eye on **FleetAlerts** for automated notifications regarding critical drag changes.

## 🤝 Contributing
Contributions to the orbital mechanics models are welcomed. Please ensure that any changes made to the drag and density calculations pass the rigorous unit tests defined in `.github/workflows/test-physics.yml`.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewDensityModel`)
3. Commit your Changes (`git commit -m 'Add support for JB2008 density model'`)
4. Push to the Branch (`git push origin feature/NewDensityModel`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.
