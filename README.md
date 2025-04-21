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

## System Module

### Overview

The system module monitors and collects metrics from various hosts in your infrastructure, providing real-time system information through both REST API and WebSockets.

### Components

1. **System Metrics Collection**:
   - Collects metrics from various hosts in your infrastructure
   - Tracks CPU, memory, disk, and network usage
   - Records system information and status

2. **Django System App**:
   - Stores system metrics in a PostgreSQL database
   - Provides REST API endpoints for data access
   - Offers WebSocket connections for real-time updates
   - Automatically cleans up old data (keeps 6 hours of metrics)

### API Endpoints

- `GET /system/api/hosts/` - List all registered hosts
  ```json
  [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "hostname": "webserver01",
      "system_type": "LINUX",
      "ip_address": "192.168.1.100",
      "is_active": true,
      "last_seen": "2025-04-20T18:45:22.428584+00:00"
    },
    {
      "id": "9d7af3fa-71c5-4049-a9c9-3c78566e9821",
      "hostname": "dbserver01",
      "system_type": "LINUX",
      "ip_address": "192.168.1.101",
      "is_active": true,
      "last_seen": "2025-04-20T18:42:10.254871+00:00"
    }
  ]
  ```
  *Lists all hosts being monitored, including their basic information and online status.*

- `GET /system/api/hosts/{host_id}/` - Get detailed information about a host
  ```json
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "hostname": "webserver01",
    "system_type": "LINUX",
    "ip_address": "192.168.1.100",
    "cpu_model": "Intel(R) Xeon(R) CPU E5-2680 v4",
    "cpu_cores": 8,
    "ram_total": 16106127360,
    "gpu_model": "",
    "os_version": "Ubuntu 22.04.3 LTS",
    "is_active": true,
    "last_seen": "2025-04-20T18:45:22.428584+00:00",
    "storage_devices": [
      {
        "id": "1b19b7fe-9933-4f53-a95c-dd448b8231b7",
        "name": "/dev/sda1",
        "device_type": "SSD",
        "total_bytes": 500107862016
      }
    ],
    "network_interfaces": [
      {
        "id": "94f2ba3a-d54e-4647-bb8d-7ed15b62123c",
        "name": "eth0",
        "mac_address": "00:1B:44:11:3A:B7",
        "ip_address": "192.168.1.100",
        "is_up": true
      }
    ]
  }
  ```
  *Provides comprehensive details about a specific host, including hardware, OS, storage, and network information.*

- `GET /system/api/hosts/{host_id}/metrics/` - Get the latest metrics for a host
  ```json
  {
    "host_id": "550e8400-e29b-41d4-a716-446655440000",
    "hostname": "webserver01",
    "metrics": {
      "cpu_usage": {
        "value": 23.5,
        "unit": "%",
        "timestamp": "2025-04-20T18:45:22.428584+00:00",
        "category": "CPU"
      },
      "memory_used": {
        "value": 8487240704,
        "unit": "bytes",
        "timestamp": "2025-04-20T18:45:22.428584+00:00",
        "category": "MEMORY"
      },
      "disk_usage_root": {
        "value": 68.2,
        "unit": "%",
        "timestamp": "2025-04-20T18:45:22.428584+00:00",
        "category": "STORAGE"
      },
      "system_temperature": {
        "value": 45.7,
        "unit": "°C",
        "timestamp": "2025-04-20T18:45:22.428584+00:00",
        "category": "TEMPERATURE"
      }
    }
  }
  ```
  *Returns the most recent metrics data collected for a specific host, including CPU, memory, disk usage, and other monitored metrics.*

### WebSockets

Connect to real-time updates via WebSocket:
```
ws://server:8000/ws/system/data/
```

Note: The WebSocket path must match exactly as `/ws/system/data/` (with trailing slash).

#### WebSocket Data Format

The WebSocket sends JSON data with the following structure:
```json
{
  "timestamp": "2025-04-20T18:45:22.428584+00:00",
  "metrics": {
    "cpu_usage": {
      "value": 23.5,
      "unit": "%",
      "timestamp": "2025-04-20T18:45:22.428584+00:00",
      "category": "CPU"
    },
    "memory_used": {
      "value": 8487240704,
      "unit": "bytes",
      "timestamp": "2025-04-20T18:45:22.428584+00:00",
      "category": "MEMORY"
    },
    "disk_usage_root": {
      "value": 68.2,
      "unit": "%",
      "timestamp": "2025-04-20T18:45:22.428584+00:00",
      "category": "STORAGE"
    },
    "system_temperature": {
      "value": 45.7,
      "unit": "°C",
      "timestamp": "2025-04-20T18:45:22.428584+00:00",
      "category": "TEMPERATURE"
    }
  }
}
```

All values are numeric except for `timestamp` (ISO format) and `category` (string).

### Data Retention

The system automatically cleans up older system metrics, keeping 6 hours of historical information. This cleanup happens once per hour.

