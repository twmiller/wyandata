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
- `GET /solar/data/daily_stats/` - Get daily aggregated statistics (energy production, peaks)
- `GET /solar/data/monthly_stats/` - Get monthly aggregated statistics
- `GET /solar/data/yearly_stats/` - Get yearly aggregated statistics
- `GET /solar/data/lifetime_stats/` - Get lifetime solar production statistics
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

