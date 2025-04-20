# Wyandata

A Django-based data collection and monitoring system.

## Running the Application

To start the server:

```bash
DJANGO_SETTINGS_MODULE=wyandata.settings uvicorn wyandata.asgi:application --host 0.0.0.0 --port 8000
```

## Solar Module

### Overview

The solar module interfaces with an Epever Tracer4210AN solar charge controller to monitor and record solar power data from the system.

### Components

1. **Solar Controller Client** (`/Users/twmiller/Developer/solar_charger.py`):
   - Standalone Python script that reads data from the Epever Tracer4210AN controller via Modbus
   - Sends data to the Django API every 60 seconds
   - Automatically creates local backups if the API is unavailable

2. **Django Solar App**:
   - Stores solar controller data in a PostgreSQL database
   - Provides REST API endpoints for data access
   - Offers WebSocket connections for real-time updates
   - Automatically cleans up old data (keeps 7 days of history)

### API Endpoints

- `GET /solar/data/` - Retrieve the latest solar controller data
- `GET /solar/data/history/` - Get historical data (with parameters `hours` and `interval`)
- `GET /solar/data/stats/` - Get statistics about solar production and battery state

#### Aggregated Data Endpoints

- `GET /solar/data/daily_stats/` - Get daily aggregated statistics (energy production, peaks)
  ```json
  {
    "dates": ["2025-04-20", "2025-04-19", "2025-04-18"],
    "energy_produced": [1245.7, 1354.2, 1198.5],
    "energy_consumed": [876.3, 912.8, 892.1],
    "peak_power": [320.5, 345.2, 298.7],
    "sunshine_hours": [8.2, 9.1, 7.8]
  }
  ```
  *Provides daily energy production (Wh), consumption, peak power values (W), and effective sunshine hours for the past 30 days (default).*

- `GET /solar/data/monthly_stats/` - Get monthly aggregated statistics
  ```json
  {
    "periods": ["2025-04", "2025-03", "2025-02"],
    "energy_produced": [38.4, 35.2, 28.7],
    "energy_consumed": [24.5, 22.8, 18.9],
    "avg_daily_production": [1.28, 1.13, 1.02]
  }
  ```
  *Provides monthly energy totals (kWh) and average daily production for the past 12 months (default).*

- `GET /solar/data/yearly_stats/` - Get yearly aggregated statistics
  ```json
  {
    "years": [2025, 2024, 2023],
    "energy_produced": [432.8, 418.5, 395.7],
    "energy_consumed": [287.6, 275.9, 262.3],
    "best_months": ["2025-06", "2024-07", "2023-06"]
  }
  ```
  *Provides yearly energy totals (kWh) and identifies the most productive month of each year.*

- `GET /solar/data/lifetime_stats/` - Get lifetime solar production statistics
  ```json
  {
    "total_energy_produced": 1247.0,
    "total_energy_consumed": 825.8,
    "peak_power_ever": 412.5,
    "peak_power_date": "2024-07-15",
    "best_day_ever": "2024-07-15",
    "best_day_production": 8.74,
    "best_month_ever": "2024-07",
    "best_month_production": 45.2,
    "operational_days": 876,
    "system_install_date": "2022-05-20"
  }
  ```
  *Provides system lifetime statistics including total energy production (kWh), all-time peak values, and system age.*

- `POST /solar/upload/` - Upload new controller data (used by the client script)

### WebSockets

Connect to real-time updates via WebSocket:
```
ws://server:8000/ws/solar/data/
```

Note: The WebSocket path must match exactly as `/ws/solar/data/` (with trailing slash).

#### WebSocket Data Format

The WebSocket sends JSON data with the following structure:
```json
{
  "timestamp": "2025-04-20T18:23:42.428584+00:00",
  "pv_array": {
    "voltage": 37.34,
    "current": 2.44,
    "power": 90.92
  },
  "battery": {
    "voltage": 13.84,
    "charging_current": 6.58,
    "charging_power": 91.34,
    "temperature": 25.0
  },
  "load": {
    "voltage": 13.84,
    "current": 0.0,
    "power": 0.0
  },
  "controller": {
    "temperature": 21.97,
    "charging_mode": "2.0"
  }
}
```

All values are numeric except for `timestamp` (ISO format) and `charging_mode` (string).

### Setting Up the Solar Monitor Client

1. Install required dependencies:
```bash
pip install pymodbus requests
```

2. Configure the script:
   - Set `SERIAL_PORT` to match your USB-to-Serial connection (default: `/dev/ttyACM0`)
   - Set `API_ENDPOINT` to point to your Django server
   - Adjust `SEND_INTERVAL` if needed (default: 60 seconds)

3. Create a systemd service for persistence:
```ini
[Unit]
Description=Solar Controller Data Collection Service
After=network.target

[Service]
User=<user>
WorkingDirectory=/path/to/script/directory
ExecStart=/usr/bin/python3 /Users/twmiller/Developer/solar_charger.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Data Retention

The system automatically cleans up older solar data, keeping 7 days of historical information. This cleanup happens once per day at 2:00 AM.

