# Database Setup

This application uses PostgreSQL for persisting workflows, nodes, and connections.

## Setup Instructions

1. **Install PostgreSQL**
   - Download and install PostgreSQL from https://www.postgresql.org/download/
   - Or use Docker: `docker run --name postgres-docr -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres`

2. **Create Database**
   ```sql
   CREATE DATABASE docr_canvas;
   ```

3. **Set Environment Variable**
   Add to your `wow.env` or `.env` file:
   ```
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docr_canvas
   ```
   Adjust the connection string based on your PostgreSQL setup.

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize Database**
   The database tables will be created automatically when you start the server.

## Database Schema

- **workflows**: Stores workflow metadata
- **nodes**: Stores node instances and their configurations
- **connections**: Stores connections between nodes

## Running Without Database

The application can run without PostgreSQL. It will use in-memory storage only. You'll see a warning message but the application will continue to function.






