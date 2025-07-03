# Interactive Tutor Backend

A FastAPI-based backend application for an interactive tutoring system with WebSocket support.

## Features

- FastAPI web framework
- WebSocket support for real-time communication
- CORS configuration for localhost development
- Modular structure with separate routes and logic folders
- Learning interface WebSocket endpoint

## Project Structure

```
interactive-tutor-be/
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
├── routes/                    # API routes
│   ├── __init__.py
│   └── websocket_routes.py    # WebSocket routes
├── logic/                     # Business logic
│   ├── __init__.py
│   ├── websocket_manager.py   # WebSocket connection management
│   └── learning_interface.py  # Learning interface logic
└── README.md
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### HTTP Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

### WebSocket Endpoints
- `WS /learning-interface` - Main learning interface WebSocket

## WebSocket Message Types

The `/learning-interface` WebSocket endpoint supports the following message types:

### Client to Server Messages

1. **Ping**
```json
{
  "type": "ping"
}
```

2. **Learning Request**
```json
{
  "type": "learning_request",
  "topic": "mathematics",
  "difficulty": "beginner"
}
```

3. **User Response**
```json
{
  "type": "user_response",
  "content": "user input text",
  "session_id": "session_123"
}
```

4. **Session Start**
```json
{
  "type": "session_start",
  "session_id": "session_123",
  "user_name": "John Doe"
}
```

5. **Session End**
```json
{
  "type": "session_end",
  "session_id": "session_123"
}
```

### Server to Client Responses

The server responds with appropriate JSON messages based on the request type, including error handling and timestamps.

## CORS Configuration

The application is configured to allow CORS requests from:
- http://localhost:3000
- http://localhost:3001
- http://localhost:8000
- http://127.0.0.1:3000
- http://127.0.0.1:3001
- http://127.0.0.1:8000

## Development

To run in development mode with auto-reload:
```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000` 