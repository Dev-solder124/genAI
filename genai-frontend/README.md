# EmpathicAI Frontend Integration

This document explains how the React (Vite) frontend talks to the Flask backend, the requirements, and how to run both in development.


###need to figure about few stuff like
- authentication
- routing interfaces

## Integration Overview

- The frontend uses the browser Fetch API to send JSON requests to the backend endpoints, such as POST /consent and POST /dialogflow-webhook, and reads JSON responses (e.g., fulfillment_response) to render chat messages.
- During development, a Vite dev proxy forwards all requests that begin with /api to the Flask server running at http://127.0.0.1:8080, avoiding cross‑origin issues without changing client code.
- Example flow:
  - Onboarding page creates a user and sends consent via POST /api/consent.
  - Chat page sends messages via POST /api/dialogflow-webhook and displays the bot reply from the returned JSON.

## Requirements

- Backend
  - Python 3.11
  - Virtual environment with project dependencies installed (requirements.txt)
  - Flask backend running on http://127.0.0.1:8080
  - Any required environment variables for backend services (e.g., credentials) set before starting

- Frontend
  - Node.js (LTS recommended)
  - npm

## How to Run (Development)

1) Start the backend (Flask)
- From the backend folder:
  - Create and activate a Python 3.11 virtual environment
  - Install dependencies: `python -m pip install -r requirements.txt`
  - Export any required environment variables (e.g., credentials)
  - Run the server: `python main.py`
- Confirm it’s healthy by opening `http://127.0.0.1:8080/health` in a browser.

2) Start the frontend (Vite + React)
- From the frontend folder (genai-frontend):
  - Install dependencies: `npm install`
  - Start the dev server: `npm run dev`
  - Open the local URL printed in the terminal (for example, `http://127.0.0.1:5173`)

## Dev Proxy (Vite)

- The dev proxy is configured so that frontend calls to `/api/*` are forwarded to the Flask backend at `http://127.0.0.1:8080`.
- Typical Vite config snippet (vite.config.js):

