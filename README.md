Project Setup and Run Guide

Prerequisites
- macOS with Homebrew or Ubuntu/Debian Linux
- Internet access and sudo privileges for installing packages

One-command setup (installs Python, MongoDB, venv, requirements, configures env)
- Make the script executable and run it:
  chmod +x setup.sh
  ./setup.sh
- The script will:
  - Install Python and tools
  - Install and start MongoDB Community
  - Create an application database and user
  - Create a .env file with Mongo and app settings (including API secret and port)

Manual setup (if you prefer)
1) Create and activate a virtual environment
   - python -m pip install --upgrade pip virtualenv
   - virtualenv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows (PowerShell): .\.venv\Scripts\Activate.ps1

2) Install dependencies
   - pip install -r requirements.txt

3) Start MongoDB
   - Local default URI is mongodb://localhost:27017
   - Start locally with: mongod (service or brew services or systemctl)

4) Configure environment
   - Create a .env file in the project root. Supported variables:
     - MONGO_HOST (e.g., localhost:27017)
     - MONGO_DB (default: simple_graphql_db)
     - MONGO_USERNAME
     - MONGO_PASSWORD
     - API_SECRET (required to protect the API; provide any strong random string)
     - APP_HOST (default: 0.0.0.0)
     - APP_PORT (default: 8000)

Run
- Start the API server (reads APP_HOST/APP_PORT and .env automatically):
  python app.py
- Or with uvicorn directly:
  uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Security: API secret on every request
- All endpoints require the following header when API_SECRET is set in .env:
  X-API-SECRET: <your_secret_here>
- Example with curl:
  curl -H "X-API-SECRET: $API_SECRET" http://127.0.0.1:8000/

GraphQL Playground
- Open:
  http://127.0.0.1:8000/graphql

Troubleshooting
- 401 Unauthorized: Ensure you are sending X-API-SECRET header matching API_SECRET in .env
- Mongo connection errors: ensure mongod is running and MONGO_* env values are correct.
- Module not found (uvicorn/fastapi/etc.): verify the virtualenv is activated and dependencies installed.


Docker (Containers)
- Prerequisites: Docker and Docker Compose installed.
- Copy .env.example to .env and adjust values as needed (for compose, MONGO_HOST should be mongo:27017):
  cp .env.example .env
- Build and start containers:
  docker compose up --build
- The API will be available at:
  http://127.0.0.1:${APP_PORT:-8000}/graphql
- Default MongoDB connection inside the Docker network uses the hostname mongo with credentials from .env (MONGO_USERNAME/MONGO_PASSWORD).
- Database schema/init: on first run, the Mongo container executes scripts from docker/initdb (mounted to /docker-entrypoint-initdb.d) and creates the `documents` collection with a unique index on `identifier` in the database defined by MONGO_DB.
- To run in development with auto-reload:
  - Set UVICORN_RELOAD=true in .env
  - Uncomment the volumes section for the app service in docker-compose.yml

Stopping and cleanup
- Stop containers: docker compose down
- Stop and remove volumes (including Mongo data): docker compose down -v
