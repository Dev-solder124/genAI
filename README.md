# genai-chatbot — Intelligent-memory Mental-Health Chatbot (Vertex AI + Firestore)

**Status:** ✅ fully-functional / deployment-ready

This README documents the project's architecture, setup, and deployment.

---

## Project Overview

This project is a mental-health-focused chatbot that implements a robust long-term memory system powered by Google Cloud's Vertex AI and Firestore. Unlike traditional chatbots, it intelligently decides what to remember, creating a high-quality, curated memory of the user's journey.

- **Intelligent Memory Creation:** Instead of saving every interaction, a generative model first analyzes each conversation turn to determine if it contains **significant information**. Only meaningful exchanges are saved, preventing memory clutter.
- **Long-Term Memory:** Significant conversation chunks are summarized by a generative model and saved to Firestore with vector embeddings for semantic retrieval.
- **Semantic Retrieval:** On each new user message, the system performs a vector search to find the most relevant past conversation summaries, prepending them to the prompt for a deeply personalized and continuous user experience.

### Core Components

- **Flask Webhook Server:** `main.py` — A robust server with multiple endpoints, compatible with any webhook-based client.
- **Vertex AI Gemini Models:** Uses the latest Gemini models (e.g., `gemini-1.5-flash`) for intelligent, empathetic responses and for analyzing/summarizing conversations.
- **Vertex AI Embeddings:** Uses `text-embedding-004` to convert text summaries into vectors for semantic search.
- **Google Cloud Firestore:** A scalable NoSQL database for persistent storage of:
  - `users`: A collection where each user document contains a `profile` map (with username and consent) and a sub-collection for their memories.
  - `memories`: A sub-collection for each user containing long-term summarized conversations with vector embeddings.
- **Privacy Controls:** A simple consent flow and a dedicated endpoint for users to delete their long-term memories on demand.

---

## File Structure

```
genai-chatbot/
├─ main.py            # Flask webhook, memory logic, and Vertex AI integration
├─ chat.py            # Interactive command-line client for testing
├─ requirements.txt   # Python dependencies
├─ README.md          # (This file)
├─ .gitignore
├─ key.json           # Service account key (NEVER commit to Git)
└─ venv/              # Python virtual environment
```

### .gitignore

Ensure your `.gitignore` contains at least the following to protect sensitive information:

```gitignore
# Python
.venv/
venv/
__pycache__/
*.pyc

# Sensitive Files
key.json
.env
*.log
chat_users_data.json
chat_history.json
current_user.json
```

---

## Prerequisites

- Python 3.10+
- A Google Cloud Project with the **Vertex AI API** enabled.
- A Firestore database created in **Native mode**.
- `gcloud` CLI configured and authenticated (`gcloud auth application-default login`).
- A service account JSON key (`key.json`) with the following IAM roles:
  - `Vertex AI User` (`roles/aiplatform.user`)
  - `Cloud Datastore User` (`roles/datastore.user`)

---

## Installation

### requirements.txt

```txt
Flask==3.0.3
google-cloud-firestore==2.16.0
google-cloud-aiplatform==1.56.0
vertexai
numpy==1.26.4
requests==2.32.3
```

### Install Dependencies

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Variables

Set the path to your service account key. This allows the application to authenticate with Google Cloud.

**PowerShell (temporary for current session):**

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\key.json"
```

It is also recommended to set your Google Cloud project ID:

```powershell
setx GOOGLE_CLOUD_PROJECT "your-gcp-project-id"
```

---

## API Endpoints

- `POST /dialogflow-webhook`: The main endpoint for chatbot interactions.
- `POST /consent`: Allows a user to grant consent for memory storage and updates their profile (e.g., username).
- `POST /delete_memories`: Deletes all long-term memories associated with a `user_id`.
- `GET /health`: A health check endpoint that verifies connectivity to Firestore and Vertex AI.
- `GET /debug/models`: A debug endpoint to list available models in your project's region.

---

## How to Run Locally

1. **Start the Server:**

   ```powershell
   # Activate your virtual environment
   .\venv\Scripts\Activate.ps1

   # Run the Flask server
   python main.py
   ```

   The server will start on `http://127.0.0.1:8080`.

2. **Run the Client:**
   In a **second terminal**, start the interactive chat client.

   ```powershell
   # Activate your virtual environment
   .\venv\Scripts\Activate.ps1

   # Run the chat client
   python chat.py
   ```

---

## Deployment (Cloud Run)

You can easily deploy this Flask application as a serverless container on Cloud Run.

```bash
# Submit a build of your container image to Google Container Registry
gcloud builds submit --tag gcr.io/your-gcp-project-id/genai-chatbot

# Deploy the container image to Cloud Run
gcloud run deploy genai-chatbot \
  --image gcr.io/your-gcp-project-id/genai-chatbot \
  --region=asia-south1 \
  --platform=managed \
  --allow-unauthenticated
```

*Note: `--allow-unauthenticated` makes the webhook public. For production, secure your webhook using IAM.*

---

## Troubleshooting & Lessons Learned

- **Symptom:** Health check fails with `ERROR: All models failed`.

  - **Solution:** Use **version-less model names** (e.g., `gemini-1.5-flash`) to always point to the latest stable release. Ensure you are using the modern, high-level `vertexai.generative_models.GenerativeModel` SDK.

- **Symptom:** `404 Not Found: Publisher Model ... was not found` error.

  - **Solution:** The specific model string does not exist in your project's region. Check the official documentation for available models.

- **Warning:** `ALTS creds ignored. Not running on GCP...` in logs.

  - **Solution:** This is a benign warning. It can be **safely ignored** during local development when authenticating with a service account key.

---

## Roadmap

- **Incorporate Time-Based Context:** Analyze memory timestamps to adapt the bot's tone based on user patterns (e.g., being more gentle during late-night conversations).
- **Advanced Retrieval:** Integrate **Vertex AI Matching Engine** (formerly Vector Search) for faster and more scalable retrieval of long-term memories.
- **Frontend UI:** Develop a simple frontend using a framework like React or Vue.js.
- **Enhanced Security:** Secure the Cloud Run webhook to only accept requests from authorized sources.

---

### Acknowledgements

This project was brought to its final, working state through a fun and collaborative debugging session. A special thanks for the great journey!

---

## License

MIT License — Please ensure you are compliant with all privacy regulations when handling user data.


# Frontend integration with backend(Flask API)

genai-frontend/
├─ vite.config.js
├─ index.html
├─ package.json
└─ src/
   ├─ main.jsx
   ├─ App.jsx
   ├─ index.css                #theme & layout (brand left, centered title)
   ├─ lib/
   │  ├─ api.js               # fetch helpers for /consent, /dialogflow-webhook, /delete_memories
   │  └─ storage.js           # localStorage for users, current user, chat history (capped to 1000)
   └─ pages/
      ├─ Onboarding.jsx       # create user, consent; POST /api/consent; navigate to /chat
      ├─ Onboarding.module.css
      ├─ Users.jsx            # list/select/delete users; delete calls /api/delete_memories
      ├─ Settings.jsx         # change username, reset consent (server re-asks next chat)
      ├─ Chat.jsx             # send messages via /api/dialogflow-webhook; dark chat UI
      └─ Chat.module.css


## Frontend (React + Vite)
The frontend is a Vite + React single-page app that talks to the Flask backend over HTTP using the browser Fetch API, sending and receiving JSON for all chat operations. It includes an onboarding flow to create a user and record consent, then routes to a dark-themed chat screen with “EmpathicAI” branded in the header and distinct left/right message bubbles for bot and user.

## How it communicates
The app calls these backend endpoints via fetch:

POST /api/consent to register a user and store consent.

POST /api/dialogflow-webhook to send messages and receive bot replies from fulfillment_response.

POST /api/delete_memories to clear server-side memories for a user.

During development, a dev proxy forwards /api/* from the Vite server to the Flask server on http://127.0.0.1:8080, avoiding CORS and keeping client code simple.

## Requirements (frontend)
Node.js (LTS recommended) and npm.

A running backend on http://127.0.0.1:8080 with a healthy /health endpoint.

The frontend source under genai-frontend with the Vite project files and pages (Onboarding, Chat, Users, Settings).

Setup and run (frontend)
From genai-frontend:

Install dependencies:

npm install

Start the dev server:

npm run dev

Open the local URL printed in the terminal (for example, http://127.0.0.1:5173).

Keep the Flask backend running on 127.0.0.1:8080 so the dev proxy can forward /api calls.

