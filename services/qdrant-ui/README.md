# Qdrant UI

A simple web-based interface for managing Qdrant vector database.

## Features

- **Collection Management**: Create, view, and delete collections
- **Vector Search**: Search for similar vectors in collections
- **Point Management**: Add, update, and delete points
- **API Documentation**: Built-in API reference
- **Real-time Updates**: Live connection to Qdrant API

## Quick Start

### Prerequisites
- Qdrant running on `http://localhost:6333`
- Python 3.x

### Start the UI
```bash
# From the services directory
./scripts/start-qdrant-ui.sh

# Or manually
cd qdrant-ui
python3 server.py
```

### Access the UI
Open your browser and go to: `http://localhost:7070/index.html`

## Usage

### Overview Tab
- View database status and version
- Quick access to common actions

### Collections Tab
- **Create Collection**: Specify name, vector size, and distance metric
- **View Collections**: See all collections with point counts
- **Delete Collections**: Remove collections (⚠️ destructive action)

### Search Tab
- **Select Collection**: Choose which collection to search
- **Enter Vector**: Provide comma-separated vector values
- **Set Limit**: Number of results to return
- **View Results**: See similarity scores and payloads

### Points Tab
- **Upsert Points**: Add or update points with vectors and payloads
- **Delete Points**: Remove specific points by ID
- **JSON Payload**: Add metadata as JSON

### API Tab
- **Endpoint Reference**: List of available API endpoints
- **Example Usage**: Sample curl commands

## API Endpoints

The UI connects to these Qdrant endpoints:
- `GET /` - Health check
- `GET /collections` - List collections
- `POST /collections` - Create collection
- `DELETE /collections/{name}` - Delete collection
- `GET /collections/{name}` - Get collection info
- `POST /collections/{name}/points` - Upsert points
- `POST /collections/{name}/points/search` - Search points
- `DELETE /collections/{name}/points` - Delete points

## Configuration

The UI is configured to connect to:
- **Qdrant URL**: `http://localhost:6333`
- **Port**: `7070`

To change these settings, edit the `server.py` file.

## Troubleshooting

### UI won't start
- Check if Python 3 is installed: `python3 --version`
- Verify Qdrant is running: `curl http://localhost:6333/`
- Check if port 7070 is available: `netstat -tlnp | grep 7070`

### Can't connect to Qdrant
- Ensure Qdrant container is running: `docker ps | grep qdrant`
- Check Qdrant logs: `docker logs mep-qdrant`
- Verify API is accessible: `curl http://localhost:6333/collections`

### CORS errors
- The server includes CORS headers for cross-origin requests
- If issues persist, check browser console for specific errors

## Development

### File Structure
```
qdrant-ui/
├── index.html      # Main UI interface
├── server.py       # Python HTTP server
└── README.md       # This file
```

### Customization
- Modify `index.html` to change the UI
- Update `server.py` to change server configuration
- Add new features by extending the JavaScript functions

### Adding Features
1. Add new tabs in the HTML
2. Create corresponding JavaScript functions
3. Update the server if needed
4. Test with the Qdrant API 