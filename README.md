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

