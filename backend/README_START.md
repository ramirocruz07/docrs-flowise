# How to Start the Backend Server

## Quick Start

### Windows:
Double-click `start_server.bat` or run:
```bash
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Mac/Linux:
```bash
cd backend
chmod +x start_server.sh
./start_server.sh
```

Or run directly:
```bash
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Verify Server is Running

1. Open your browser and go to: http://localhost:8000
2. You should see: `{"message":"Docr Canvas API","status":"running"}`

## Troubleshooting

- **Port 8000 already in use**: Change the port in the command or kill the process using port 8000
- **Module not found errors**: Make sure you've installed dependencies: `pip install -r requirements.txt`
- **API Key not found**: Make sure `wow.env` file exists in the backend directory with your `OPENAI_API_KEY`

## Server Status

When the server starts successfully, you should see:
- `✓ OPENAI_API_KEY loaded successfully` (if API key is set)
- `INFO:     Uvicorn running on http://0.0.0.0:8000`
- `INFO:     Application startup complete.`








