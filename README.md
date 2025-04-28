# Wyandata

A Django-based data collection and monitoring system.

## Running the Application

To start the server:

```bash
DJANGO_SETTINGS_MODULE=wyandata.settings uvicorn wyandata.asgi:application --host 0.0.0.0 --port 8000
```

## Applications

### Books

A library management system with OpenLibrary integration for book metadata.

#### Features:

- Track books, authors, genres, and publishers
- User-specific book collections with reading status tracking
- Integration with OpenLibrary API for metadata retrieval
- Comprehensive search capabilities

#### API Endpoints:

**1. Get Books List / Create Book**

- URL: `/books/api/books/`
- Methods: `GET`, `POST`

**GET**: Retrieves a list of all books in the library.
- Query Parameters:
  - `q`: Search query for title, author, or description
  - `genre`: Filter by genre slug
- Example response:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "The Hitchhiker's Guide to the Galaxy",
    "slug": "the-hitchhikers-guide-to-the-galaxy",
    "authors": [
      {
        "id": "9d7af3fa-71c5-4049-a9c9-3c78566e9821",
        "name": "Douglas Adams",
        "slug": "douglas-adams",
        "biography": "Douglas Noel Adams was an English author...",
        "birth_date": "1952-03-11",
        "death_date": "2001-05-11",
        "ol_author_key": "OL272947A"
      }
    ],
    "genres": [
      {
        "id": "1b19b7fe-9933-4f53-a95c-dd448b8231b7",
        "name": "Science Fiction",
        "slug": "science-fiction"
      },
      {
        "id": "94f2ba3a-d54e-4647-bb8d-7ed15b62123c",
        "name": "Comedy",
        "slug": "comedy"
      }
    ],
    "publication_date": "1979-10-12",
    "isbn_10": "0345391802",
    "isbn_13": "9780345391803",
    "description": "Seconds before the Earth is demolished...",
    "cover_image": "/media/book_covers/hitchhiker.jpg",
    "page_count": 224
  }
]
```

**POST**: Creates a new book.
- Content Type: `application/json`
- Example request:
```json
{
  "title": "Project Hail Mary",
  "description": "A novel about a lone astronaut who must save the earth from disaster",
  "isbn_13": "9780593135204",
  "publication_date": "2021-05-04",
  "publisher_id": "23456789-abcd-1234-ef56-789012345678",
  "language": "eng",
  "page_count": 496
}
```
- Notes: 
  - After creating the book, use separate requests to add authors and genres
  - The `slug` field is automatically generated from the title

**2. Get Book Details / Update Book / Delete Book**

- URL: `/books/api/books/{book_slug}/`
- Methods: `GET`, `PUT`, `DELETE`

**GET**: Retrieves detailed information about a specific book.
- Example response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Hitchhiker's Guide to the Galaxy",
  "slug": "the-hitchhikers-guide-to-the-galaxy",
  "authors": [
    {
      "id": "9d7af3fa-71c5-4049-a9c9-3c78566e9821",
      "name": "Douglas Adams",
      "slug": "douglas-adams",
      "biography": "Douglas Noel Adams was an English author...",
      "birth_date": "1952-03-11",
      "death_date": "2001-05-11",
      "ol_author_key": "OL272947A"
    }
  ],
  "genres": [
    {
      "id": "1b19b7fe-9933-4f53-a95c-dd448b8231b7",
      "name": "Science Fiction",
      "slug": "science-fiction"
    },
    {
      "id": "94f2ba3a-d54e-4647-bb8d-7ed15b62123c",
      "name": "Comedy",
      "slug": "comedy"
    }
  ],
  "publisher": {
    "id": "23456789-abcd-1234-ef56-789012345678",
    "name": "Pan Books",
    "website": "https://www.panmacmillan.com/"
  },
  "publication_date": "1979-10-12",
  "isbn_10": "0345391802",
  "isbn_13": "9780345391803",
  "description": "Seconds before the Earth is demolished...",
  "cover_image": "/media/book_covers/hitchhiker.jpg",
  "page_count": 224,
  "ol_work_key": "OL45883W",
  "ol_edition_key": "OL22545361M",
  "language": "eng",
  "added_date": "2025-04-15T14:22:31.742562",
  "updated_date": "2025-04-15T14:22:31.742562"
}
```

**PUT**: Updates an existing book.
- Content Type: `application/json`
- Example request:
```json
{
  "description": "Updated description of the book",
  "page_count": 512
}
```
- Notes: 
  - Only provide the fields you want to update
  - To update authors or genres, include them in the request

**DELETE**: Removes a book.
- Returns: 204 No Content on success

**3. Get Authors List / Create Author**

- URL: `/books/api/authors/`
- Methods: `GET`, `POST`

**GET**: Retrieves a list of all authors.
- Query Parameters:
  - `q`: Search query for author name
- Example response:
```json
[
  {
    "id": "9d7af3fa-71c5-4049-a9c9-3c78566e9821",
    "name": "Douglas Adams",
    "slug": "douglas-adams",
    "biography": "Douglas Noel Adams was an English author...",
    "birth_date": "1952-03-11",
    "death_date": "2001-05-11",
    "ol_author_key": "OL272947A"
  },
  {
    "id": "1b19b7fe-9933-4f53-a95c-dd448b8231b7",
    "name": "Jane Austen",
    "slug": "jane-austen",
    "biography": "Jane Austen was an English novelist...",
    "birth_date": "1775-12-16",
    "death_date": "1817-07-18",
    "ol_author_key": "OL21594A"
  }
]
```

**POST**: Creates a new author.
- Content Type: `application/json`
- Example request:
```json
{
  "name": "Andy Weir",
  "biography": "Andy Weir is an American novelist and former computer programmer.",
  "birth_date": "1972-06-16"
}
```
- Notes: The `slug` field is automatically generated from the name

**4. Get Author Details / Update Author / Delete Author**

- URL: `/books/api/authors/{author_slug}/`
- Methods: `GET`, `PUT`, `DELETE`

**GET**: Retrieves detailed information about a specific author.
- Example response:
```json
{
  "id": "9d7af3fa-71c5-4049-a9c9-3c78566e9821",
  "name": "Douglas Adams",
  "slug": "douglas-adams",
  "biography": "Douglas Noel Adams was an English author...",
  "birth_date": "1952-03-11",
  "death_date": "2001-05-11",
  "ol_author_key": "OL272947A"
}
```

**PUT**: Updates an existing author.
- Content Type: `application/json`
- Example request:
```json
{
  "biography": "Updated biography for this author",
  "death_date": "2023-01-01"
}
```
- Notes: Only provide the fields you want to update

**DELETE**: Removes an author.
- Returns: 204 No Content on success

#### OpenLibrary Integration

The Books app integrates with OpenLibrary API to fetch book metadata:

- Search for books via OpenLibrary
- Import book details including covers, descriptions, and author information
- Link books to their OpenLibrary records for additional information

### Weather

The Weather app collects data from Fineoffset weather stations and sensors.

#### Supported Weather Stations and Sensors:
- Fineoffset-WH24 Outdoor Weather Station
- Fineoffset-WH65 Outdoor Weather Station
- Fineoffset-WN32P Indoor Temperature/Humidity Sensor

#### API Endpoints:

**1. Receive Weather Data**

Endpoint to receive data from rtl_433 weather station receiver.

- URL: `/api/weather/receive/`
- Method: `POST`
- Content-Type: `application/json`
- Example payload:
```json
{
  "time": "2025-04-21 13:34:47",
  "model": "Fineoffset-WH24",
  "id": 182,
  "battery_ok": 1,
  "temperature_C": 5.500,
  "humidity": 63,
  "wind_dir_deg": 38,
  "wind_avg_m_s": 0.000,
  "wind_max_m_s": 0.000,
  "rain_mm": 1461.300,
  "uv": 83,
  "uvi": 0,
  "light_lux": 10602.000,
  "mic": "CRC"
}
```

**2. Get Current Weather Data**

Endpoint to retrieve the most recent weather data.

- URL: `/api/weather/current/`
- Method: `GET`
- Example response:
```json
{
  "status": "success",
  "timestamp": "2025-04-21T13:34:47-06:00",
  "outdoor": {
    "model": "Fineoffset-WH24",
    "sensor_id": 182,
    "temperature": {
      "celsius": 5.5,
      "fahrenheit": 41.9
    },
    "humidity": 63,
    "wind": {
      "direction_degrees": 38,
      "direction_cardinal": "NE",
      "speed": {
        "avg_m_s": 0.0,
        "avg_mph": 0.0,
        "max_m_s": 0.0,
        "max_mph": 0.0
      }
    },
    "rain": {
      "total_mm": 1461.3,
      "total_inches": 57.53,
      "since_previous_inches": 0.06
    },
    "uv": 83,
    "uvi": 0,
    "light_lux": 10602.0
  },
  "indoor": {
    "model": "Fineoffset-WN32P",
    "sensor_id": 105,
    "temperature": {
      "celsius": 21.8,
      "fahrenheit": 71.2
    },
    "humidity": 42,
    "timestamp": "2025-04-21T14:03:12-06:00"
  }
}
```

**3. Get Daily Weather Summaries**

Endpoint to retrieve daily weather statistics.

- URL: `/api/weather/daily/`
- Method: `GET`
- Query Parameters:
  - `days`: Number of days to retrieve (default: 7, max: 365)
- Example response:
```json
{
  "status": "success",
  "days": 7,
  "summaries": [
    {
      "date": "2025-04-21",
      "temperature": {
        "min_c": 3.2,
        "max_c": 12.8,
        "avg_c": 8.5,
        "min_f": 37.8,
        "max_f": 55.0,
        "avg_f": 47.3
      },
      "humidity": {
        "min": 42,
        "max": 78,
        "avg": 65
      },
      "rainfall": {
        "total_mm": 8.2,
        "total_inches": 0.32
      },
      "wind": {
        "max_speed_mph": 15.8,
        "predominant_direction": "NW"
      },
      "max_uvi": 3
    },
    // Additional days...
  ]
}
```

**4. Get Monthly Weather Summaries**

Endpoint to retrieve monthly weather statistics.

- URL: `/api/weather/monthly/`
- Method: `GET`
- Query Parameters:
  - `months`: Number of months to retrieve (default: 12, max: 60)
- Example response:
```json
{
  "status": "success",
  "months": 12,
  "summaries": [
    {
      "year_month": "2025-04",
      "temperature": {
        "min_c": -2.8,
        "max_c": 24.3,
        "avg_c": 10.7,
        "min_f": 27.0,
        "max_f": 75.7,
        "avg_f": 51.3
      },
      "rainfall": {
        "total_mm": 52.4,
        "total_inches": 2.06,
        "rainy_days": 8
      },
      "max_wind_speed_mph": 34.6
    },
    // Additional months...
  ]
}
```

**5. Get Recent Weather Readings**

Endpoint to retrieve a specific number of recent weather readings.

- URL: `/api/weather/recent/`
- Method: `GET`
- Query Parameters:
  - `count`: Number of readings to retrieve (default: 100, max: 1000)
  - `sensor_id`: Optional filter for a specific sensor
- Example response:
```json
{
  "status": "success",
  "count": 100,
  "time_info": {
    "start_time": "2025-04-21T10:00:00-06:00",
    "end_time": "2025-04-21T14:03:12-06:00",
    "duration_seconds": 14592,
    "duration_minutes": 243.2,
    "duration_hours": 4.05
  },
  "readings": [
    {
      "timestamp": "2025-04-21T14:03:12-06:00",
      "model": "Fineoffset-WH24",
      "sensor_id": 182,
      "temperature": {
        "celsius": 5.5,
        "fahrenheit": 41.9
      },
      "humidity": 63,
      "wind": {
        "direction_degrees": 38,
        "direction_cardinal": "NE",
        "speed": {
          "avg_m_s": 0.0,
          "avg_mph": 0.0,
          "max_m_s": 0.0,
          "max_mph": 0.0
        }
      },
      "rain": {
        "total_mm": 1461.3,
        "total_inches": 57.53,
        "since_previous_inches": 0.06
      },
      "uv": 83,
      "uvi": 0,
      "light_lux": 10602.0
    },
    // Additional readings...
  ]
}
```

### WebSockets

Connect to real-time weather updates via WebSocket:
```
ws://server:8000/ws/weather/data/
```

Note: The WebSocket path must match exactly as `/ws/weather/data/` (with trailing slash).

#### WebSocket Data Format

The WebSocket sends JSON data with the following structure:
```json
{
  "timestamp": "2025-04-21T13:34:47-06:00",
  "outdoor": {
    "model": "Fineoffset-WH24",
    "sensor_id": 182,
    "temperature": {
      "celsius": 5.5,
      "fahrenheit": 41.9
    },
    "humidity": 63,
    "wind": {
      "direction_degrees": 38,
      "direction_cardinal": "NE",
      "speed": {
        "avg_m_s": 0.0,
        "avg_mph": 0.0,
        "max_m_s": 0.0,
        "max_mph": 0.0
      }
    },
    "rain": {
      "total_mm": 1461.3,
      "total_inches": 57.53,
      "since_previous_inches": 0.06
    },
    "uv": 83,
    "uvi": 0,
    "light_lux": 10602.0
  },
  "indoor": {
    "model": "Fineoffset-WN32P",
    "sensor_id": 105,
    "temperature": {
      "celsius": 21.8,
      "fahrenheit": 71.2
    },
    "humidity": 42,
    "timestamp": "2025-04-21T14:03:12-06:00"
  }
}
```

All values are consistent with the REST API format, using the same structure for measurements.

### Data Retention

The weather app implements the following data retention policies:

- **Raw Weather Readings**: 7 days of detailed sensor data (approx. 15-30 second intervals)
- **Daily Summaries**: Permanently stored (minimal storage requirements)
- **Monthly Summaries**: Permanently stored (minimal storage requirements)

To clean up old weather data manually, run:

```bash
# Clean up data older than 7 days (default)
python manage.py cleanup_weather_data

# Clean up data older than a specific number of days
python manage.py cleanup_weather_data --days=14

# Perform a dry run to see what would be deleted
python manage.py cleanup_weather_data --dry-run
```

### Weather Data Updates

To generate daily and monthly weather summaries manually, run:

```bash
# Process the last 7 days (default)
python manage.py generate_weather_summaries

# Process a specific number of days
python manage.py generate_weather_summaries --days=30

# Force regeneration of existing summaries
python manage.py generate_weather_summaries --regenerate
```

### Scheduled Tasks

The application uses django-crontab for scheduling regular tasks:

```bash
# List all configured cron jobs
python manage.py crontab show

# Add all configured cron jobs
python manage.py crontab add

# Remove all cron jobs
python manage.py crontab remove
```

The following cron jobs are configured:
- Generate weather summaries (daily at 12:05 AM)
- Clean up old weather data (daily at 3:15 AM, keeping 7 days of raw data)

### Solar

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

### System

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

- `GET /system/api/hosts/{host_id}/metrics/history/` - Get historical metrics for a host
  ```json
  {
    "host_id": "550e8400-e29b-41d4-a716-446655440000",
    "hostname": "webserver01",
    "count_requested": 180,
    "time_range": {
      "start": "2025-04-22T08:03:14.127654",
      "end": "2025-04-22T08:35:05.294872",
      "duration_minutes": 31.85
    },
    "interval_minutes": 5,
    "metrics": [
      {
        "name": "cpu_usage",
        "category": "CPU",
        "unit": "%",
        "data_points": [
          {"timestamp": "2025-04-22T08:03:14.127654", "value": 15.2},
          {"timestamp": "2025-04-22T08:08:22.485921", "value": 18.7},
          {"timestamp": "2025-04-22T08:13:45.723109", "value": 22.1},
          // More data points...
          {"timestamp": "2025-04-22T08:35:05.294872", "value": 23.5}
        ]
      },
      // More metrics...
    ]
  }
  ```
  *Returns time-series metrics data for a specific host. The endpoint retrieves the most recent metrics and groups them by type. Query parameters:*
  - `count`: Number of most recent metrics to retrieve (default: 180, max: 1000)
  - `interval`: Sampling interval in minutes for downsampling (default: 5, min: 1, max: 60)
  - `metrics`: Comma-separated list of metric names to include (default: all available metrics)

#### Examples of using the metrics parameter:

```
# Get only CPU usage metrics
GET /system/api/hosts/550e8400-e29b-41d4-a716-446655440000/metrics/history/?metrics=cpu_usage

# Get multiple specific metrics
GET /system/api/hosts/550e8400-e29b-41d4-a716-446655440000/metrics/history/?metrics=cpu_usage,memory_used,disk_percent_/

# Get temperature metrics with more data points
GET /system/api/hosts/550e8400-e29b-41d4-a716-446655440000/metrics/history/?metrics=temp_cpu_0,temp_cpu_1&count=500

# Get network metrics with finer interval
GET /system/api/hosts/550e8400-e29b-41d4-a716-446655440000/metrics/history/?metrics=net_bytes_recv_eth0,net_bytes_sent_eth0&interval=1
```

The response structure remains the same, but only includes the requested metrics:

```json
{
  "host_id": "550e8400-e29b-41d4-a716-446655440000",
  "hostname": "webserver01",
  "count_requested": 180,
  "data_count": 180,
  "interval_minutes": 5,
  "metrics": [
    {
      "name": "cpu_usage",
      "category": "CPU",
      "unit": "%",
      "data_points": [
        {"timestamp": "2025-04-22T08:03:14.127654", "value": 15.2},
        // More data points...
      ]
    }
  ],
  "total_metrics_in_db": 8880
}
```

- `GET /system/api/hosts/{host_id}/metrics/available/` - Get available metrics for a host
  ```json
  {
    "host_id": "550e8400-e29b-41d4-a716-446655440000",
    "hostname": "webserver01",
    "latest_data_timestamp": "2025-04-22T15:42:18.124657",
    "metrics": {
      "CPU": [
        {
          "name": "cpu_usage",
          "description": "Overall CPU usage percentage",
          "unit": "%",
          "data_type": "FLOAT"
        },
        {
          "name": "cpu_usage_0",
          "description": "CPU core 0 usage percentage",
          "unit": "%",
          "data_type": "FLOAT"
        },
        // More CPU metrics
      ],
      "MEMORY": [
        {
          "name": "memory_used",
          "description": "Physical memory in use",
          "unit": "bytes",
          "data_type": "INT"
        },
        // More memory metrics
      ],
      "STORAGE": [
        // Storage metrics
      ],
      "NETWORK": [
        // Network metrics
      ],
      "TEMPERATURE": [
        // Temperature metrics
      ]
    }
  }
  ```
  *Returns a categorized list of all metrics available for the specified host. This helps with discovering what metrics can be requested in the history endpoint.*

### Supported System Metrics

The system tracks the following metrics for each host:

#### CPU Metrics
- `cpu_usage` - Overall CPU usage (%)
- `cpu_usage_{core}` - Per-core CPU usage (%), e.g., `cpu_usage_0`, `cpu_usage_1`
- `load_avg_1min` - 1-minute load average
- `load_avg_5min` - 5-minute load average
- `load_avg_15min` - 15-minute load average

#### Memory Metrics
- `memory_used` - Memory usage (bytes)
- `memory_free` - Free memory (bytes)
- `memory_percent` - Memory usage (%)
- `swap_used` - Swap usage (bytes)
- `swap_free` - Free swap (bytes)
- `swap_percent` - Swap usage (%)

#### Storage Metrics
- `disk_used_{mount}` - Storage used on mount point (bytes), e.g., `disk_used_/`, `disk_used_/home`
- `disk_free_{mount}` - Free storage on mount point (bytes)
- `disk_percent_{mount}` - Storage usage on mount point (%)
- `disk_io_read_{device}` - Disk read bytes for device, e.g., `disk_io_read_sda`
- `disk_io_write_{device}` - Disk write bytes for device
- `disk_io_busy_{device}` - Disk busy time for device (%)

#### Network Metrics
- `net_bytes_sent_{interface}` - Network bytes sent on interface, e.g., `net_bytes_sent_enp1s0`
- `net_bytes_recv_{interface}` - Network bytes received on interface
- `net_packets_sent_{interface}` - Network packets sent on interface
- `net_packets_recv_{interface}` - Network packets received on interface
- `net_errin_{interface}` - Incoming packet errors on interface
- `net_errout_{interface}` - Outgoing packet errors on interface

#### Process Metrics
- `process_count` - Total number of processes
- `thread_count` - Total number of threads
- `zombie_count` - Number of zombie processes

#### Temperature Metrics
- `temp_cpu_{sensor}` - CPU temperature (°C), e.g., `temp_cpu_0`, `temp_cpu_1`
- `temp_acpitz_{sensor}` - ACPI thermal zone temperature (°C)
- `temp_nvme_{device}` - NVMe drive temperature (°C)
- `temp_coretemp_{core}` - CPU core temperature (°C)
- `temp_pch_{chipset}` - Platform controller hub temperature (°C)
- `temp_iwlwifi_{sensor}` - WiFi adapter temperature (°C)
- `temp_gpu_{sensor}` - GPU temperature (°C)

#### GPU Metrics (if available)
- `gpu_usage` - GPU utilization (%)
- `gpu_memory_used` - GPU memory usage (bytes)
- `gpu_memory_percent` - GPU memory usage (%)
- `gpu_temp` - GPU temperature (°C)
- `gpu_power` - GPU power consumption (W)

#### System Metrics
- `uptime` - System uptime (seconds)
- `boot_time` - System boot time (timestamp)
- `users_logged_in` - Number of logged-in users

### WebSockets

Connect to real-time updates via WebSocket:
```
ws://server:8000/ws/system/metrics/
```

Note: The WebSocket path must match exactly as `/ws/system/metrics/` (with trailing slash).

#### WebSocket Subscription

The system WebSocket implements a subscription model. After connecting, you need to send a subscription message to receive updates for a specific host:

```json
{
  "type": "subscribe_host", 
  "host_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The server will confirm your subscription with:

```json
{
  "type": "subscription_confirmed", 
  "host_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

After subscription confirmation, you'll receive real-time metrics updates for the specified host.

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

