# Wyandata

A Django-based API-only data collection and monitoring system.

## Running the Application

To start the server:

```bash
DJANGO_SETTINGS_MODULE=wyandata.settings uvicorn wyandata.asgi:application --host 0.0.0.0 --port 8000
```

## API Endpoints

### Books API

RESTful API for book and author data management with OpenLibrary integration.

**Books Endpoints**:

- `GET /api/books/` - List all books with optional search and filtering
- `POST /api/books/` - Create a new book
- `GET /api/books/{slug}/` - Get details for a specific book
- `PUT /api/books/{slug}/` - Update a book
- `DELETE /api/books/{slug}/` - Remove a book

**Authors Endpoints**:

- `GET /api/authors/` - List all authors with optional search
- `POST /api/authors/` - Create a new author
- `GET /api/authors/{slug}/` - Get details for a specific author
- `PUT /api/authors/{slug}/` - Update an author
- `DELETE /api/authors/{slug}/` - Remove an author

### Weather API

Collection and retrieval of data from Fineoffset weather stations.

**Endpoints**:

- `POST /api/weather/receive/` - Receive data from weather station receivers
- `GET /api/weather/current/` - Get current weather data
- `GET /api/weather/recent/` - Get recent weather readings
- `GET /api/weather/daily/` - Get daily weather summaries
- `GET /api/weather/monthly/` - Get monthly weather summaries

### Solar API

Monitoring of solar power systems with Epever Tracer controller integration.

**Endpoints**:

- `GET /api/solar/data/` - Get latest solar controller data
- `GET /api/solar/data/history/` - Get historical solar data
- `GET /api/solar/data/daily_stats/` - Get daily energy production statistics
- `GET /api/solar/data/monthly_stats/` - Get monthly energy statistics
- `GET /api/solar/data/yearly_stats/` - Get yearly energy statistics
- `GET /api/solar/data/lifetime_stats/` - Get lifetime production statistics
- `POST /api/solar/upload/` - Upload controller data

### System API

System metrics collection and monitoring for infrastructure hosts.

**Endpoints**:

- `GET /api/system/hosts/` - List all monitored hosts
- `GET /api/system/hosts/{host_id}/` - Get host details
- `GET /api/system/hosts/{host_id}/metrics/` - Get latest metrics for a host
- `GET /api/system/hosts/{host_id}/metrics/history/` - Get historical metrics
- `GET /api/system/hosts/{host_id}/metrics/available/` - Get available metrics

## WebSockets

Real-time data can be accessed via WebSockets:

- Weather data: `ws://server:8000/ws/weather/data/`
- Solar data: `ws://server:8000/ws/solar/data/`
- System metrics: `ws://server:8000/ws/system/metrics/`

### System WebSocket Usage

```javascript
// Connect to the WebSocket
const socket = new WebSocket('ws://server:8000/ws/system/metrics/');

// Subscribe to a specific host
socket.onopen = () => {
  socket.send(JSON.stringify({
    type: 'subscribe_host',
    host_id: '550e8400-e29b-41d4-a716-446655440000'
  }));
};

// Handle incoming data
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Metrics update:', data);
};
```

## Data Retention

- Weather: 7 days of raw data, permanent storage of summaries
- Solar: 7 days of raw data, aggregated statistics stored permanently
- System: 6 hours of metrics data

## Management Commands

```bash
# Clean up old weather data
python manage.py cleanup_weather_data [--days=14] [--dry-run]

# Generate weather summaries
python manage.py generate_weather_summaries [--days=30] [--regenerate]

# Remove hosts
python manage.py remove_hosts [--hostname=name] [--id=uuid] [--all] [--inactive]

# Flush metrics
python manage.py flush_metrics --confirm [--host=name] [--older-than=days]
```

## Scheduled Tasks

The system uses django-crontab for scheduled maintenance:

```bash
# List all configured cron jobs
python manage.py crontab show

# Add all configured cron jobs
python manage.py crontab add

# Remove all cron jobs
python manage.py crontab remove
```

Automated tasks include:
- Daily weather summary generation
- Data cleanup for all modules
- Daily solar aggregation

# WyanData

## Satellite Data Processing

The WyanData platform includes a satellite module designed to process and manage EMWIN (Emergency Managers Weather Information Network) data received from weather satellites.

### EMWIN Data Model

The `EMWINFile` model stores meteorological data files with the following key information:

- **File Information**: filename, path, size, and modification time
- **Metadata**: WMO header, originator, product ID, etc.
- **Timing**: source datetime, timestamp, day, hour, minute
- **Station Information**: station ID, name, location, coordinates, etc.
- **Content**: text preview and file status

### API Endpoints

#### Base Endpoints

- `GET /api/satellite/emwin/` - List all EMWIN files (paginated)
- `GET /api/satellite/emwin/{id}/` - Get a specific file by ID
- `POST /api/satellite/emwin/` - Create a new EMWIN file entry
- `PUT /api/satellite/emwin/{id}/` - Update an existing file
- `DELETE /api/satellite/emwin/{id}/` - Delete a file entry

#### Filtering Options

- `GET /api/satellite/emwin/?product_id=STPTPTCN` - Filter by product ID
- `GET /api/satellite/emwin/?station_id=KWBC` - Filter by station ID
- `GET /api/satellite/emwin/?wmo_header=ABCN01` - Filter by WMO header
- `GET /api/satellite/emwin/?has_been_read=false` - Filter by read status
- `GET /api/satellite/emwin/?station_country=US&station_state=DC` - Filter by country/state

#### Search

- `GET /api/satellite/emwin/?search=washington` - Search across multiple fields

#### Sorting

- `GET /api/satellite/emwin/?ordering=-source_datetime` - Sort by source datetime (newest first)
- `GET /api/satellite/emwin/?ordering=size_bytes` - Sort by file size

#### Custom Actions

- `GET /api/satellite/emwin/categories/` - Get unique product categories
- `GET /api/satellite/emwin/stations/` - Get unique stations with file counts
- `GET /api/satellite/emwin/products/` - Get unique product IDs with counts and names
- `POST /api/satellite/emwin/mark_read/` - Mark files as read (with JSON body `{"ids": [1, 2, 3]}`)
- `POST /api/satellite/emwin/mark_unread/` - Mark files as unread (with JSON body `{"ids": [1, 2, 3]}`)

#### Combined Options

You can combine multiple query parameters:

```
GET /api/satellite/emwin/?product_id=STPTPTCN&station_country=US&ordering=-source_datetime&search=forecast
```

### Management Commands

The application includes a management command to import EMWIN files:

```bash
# Import files from a directory
python manage.py process_emwin_files /processed_lrit/emwin/2025-05-17/

# With optional parameters
python manage.py process_emwin_files /processed_lrit/emwin/2025-05-17/ --batch-size=500 --preview-length=150
```

### Model Properties

The `EMWINFile` model includes useful properties:

- `file_extension` - Returns the file extension
- `is_text_file` - Indicates if the file is a text file
- `is_image_file` - Indicates if the file is an image file
- `age_in_hours` - Returns the age of the file in hours
- `has_coordinates` - Indicates if the station has coordinates

### EMWIN Filename Format

EMWIN files follow this naming pattern:

```
A_[WMO_HEADER][ORIGINATOR][DDHHMI]_C_[COMM_ID]_[YYYYMMDDHHMMSS]_[MESSAGE_ID]-[VERSION]-[PRODUCT_ID].TXT
```

Example:

```
A_ABCN01KWBC170115_C_KWIN_20250517011502_321540-2-STPTPTCN.TXT
```

Where:
- `ABCN01` - WMO header
- `KWBC` - Originator (station)
- `170115` - Day, hour, minute (17th day, 01:15)
- `KWIN` - Communication ID
- `20250517011502` - Full timestamp (2025-05-17 01:15:02)
- `321540` - Message ID
- `2` - Version
- `STPTPTCN` - Product ID

### Example JSON Response

```json
{
  "id": 1,
  "filename": "A_ABCN01KWBC170115_C_KWIN_20250517011502_321540-2-STPTPTCN.TXT",
  "path": "/processed_lrit/emwin/2025-05-17/A_ABCN01KWBC170115_C_KWIN_20250517011502_321540-2-STPTPTCN.TXT",
  "size_bytes": 1079,
  "last_modified": "2025-05-17T07:32:00Z",
  "parsed": true,
  "wmo_header": "ABCN01",
  "originator": "KWBC",
  "comm_id": "KWIN",
  "message_id": "321540",
  "version": "2",
  "product_id": "STPTPTCN",
  "source_datetime": "2025-05-17T01:15:00Z",
  "full_timestamp": "2025-05-17T01:15:02Z",
  "day": "17",
  "hour": "01",
  "minute": "15",
  "product_name": "Spot Forecast",
  "product_category": "Forecasts/Analyses",
  "station_id": "KWBC",
  "station_name": "National Weather Service",
  "station_location": "Washington, DC",
  "station_latitude": 38.8951,
  "station_longitude": -77.0364,
  "station_elevation_meters": 25,
  "station_type": "Weather Forecast Office",
  "station_state": "DC",
  "station_country": "US",
  "preview": "First 100 characters of the file...",
  "content_size_bytes": 1079,
  "has_been_read": false,
  "created_at": "2025-05-17T07:35:12Z",
  "updated_at": "2025-05-17T07:35:12Z",
  "age_in_hours": 6.34,
  "file_extension": ".txt",
  "has_coordinates": true
}
```

### Frontend Development

When building a frontend for this API:

1. **List View**: Create a paginated table of EMWIN files with sorting and filtering.
2. **Detail View**: Show complete file details including station coordinates on a map.
3. **Search**: Add a search bar that uses the API's search capabilities.
4. **Filters**: Implement dropdown filters for product types, stations, etc.
5. **Actions**: Add buttons to mark files as read/unread.

### Required Packages

- Django
- Django REST Framework
- django-filter
- pytz

### Setup

1. Install required packages: `pip install django djangorestframework django-filter pytz`
2. Ensure 'satellite', 'rest_framework', and 'django_filters' are in INSTALLED_APPS
3. Include satellite URLs in your main urls.py: `path('', include('satellite.urls'))`
4. Apply migrations: `python manage.py migrate`
5. Import data using the management command: `python manage.py process_emwin_files /path/to/emwin/files`

