# genai-chatbot — Hybrid-memory mental-health chatbot (Vertex AI + Firestore)

**Status:** prototype / dev-ready — Flask webhook + Vertex AI + Firestore working locally.

This README documents the whole project: architecture, setup, running, testing, deployment, debugging, privacy/safety, and next steps.

---

## Project Overview

This project is a mental-health-focused chatbot that implements hybrid memory:

- **Short-term memory:** session parameters + an in-session buffer (keeps recent turns for immediate context)
- **Long-term memory:** summarized session chunks saved to Firestore with embeddings (semantic retrieval on future sessions)
- **Hybrid retrieval:** on each new input the system retrieves the top-k similar past summaries for the user and prepends them to the prompt for more continuity/personalization

### Core Components

- **Flask webhook server:** main.py — Dialogflow CX (or any client) calls `/dialogflow-webhook`
- **Vertex AI** (Vertex Generative Models + Embeddings) for generation & embeddings
- **Google Cloud Firestore** for persistent storage of:
  - users (consent, preferences)
  - session_buffers (recent turns)
  - memories (summaries + embedding vectors + metadata)
- Simple consent flow and a delete-memories endpoint to satisfy privacy needs

---

## Quick Highlights / What You Already Have

- Working main.py with endpoints:
  - `POST /dialogflow-webhook` — main webhook (Dialogflow CX compatible)
  - `POST /consent` — set user consent to store long-term memory
  - `POST /delete_memories` — remove long-term memories for a user
- Firestore integration and a simple embedding/retrieval loop
- Summarization step that runs when session buffer reaches a threshold (example: 8 turns) and saves a summary as a long-term memory
- Vertex AI call wrappers for embeddings and text generation
- Local testing capability with PowerShell / curl and ngrok if you want to expose your local server temporarily

---

## File Structure (Recommended)

```
genai-chatbot/
├─ main.py              # Flask webhook + memory code (your primary file)
├─ requirements.txt     # pip dependencies
├─ README.md           # (this file)
├─ .gitignore
├─ key.json            # service account key (NEVER commit)
├─ venv/               # virtual environment (optional)
└─ optionally: frontend/  # if you add a UI later
```

### .gitignore

Your `.gitignore` should contain at least:

```gitignore
.venv/
venv/
__pycache__/
*.pyc
key.json
.env
```

---

## Prerequisites

### Local Development

- Python 3.10+ (3.11 recommended)
- Virtual environment (venv)
- gcloud CLI configured and authenticated to your project (you used genai-bot-kdf)
- Service account JSON key with roles: `roles/aiplatform.user` and `roles/datastore.user` (or `roles/editor` for dev)
- Firestore database created (Native mode) in a chosen region (e.g. asia-south1)

### Python Packages

- Flask
- google-cloud-firestore
- google-cloud-aiplatform
- numpy
- python-dotenv (optional)

---

## Installation

### requirements.txt

```txt
Flask==2.3.2
google-cloud-firestore==2.11.0
google-cloud-aiplatform==1.26.0
numpy==1.26.0
python-dotenv==1.0.0
requests==2.31.0
```

### Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Variables (Important)

Set your service account credentials (one-time):

### PowerShell (temporary for session)
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="D:\genAI\key.json"
```

### PowerShell (permanent)
```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "D:\genAI\key.json"
```

Also set project + region if you prefer:
```powershell
setx GOOGLE_CLOUD_PROJECT "genai-bot-kdf"
setx REGION "asia-south1"
```

---

## How the System Works (Detailed)

1. **Incoming message** → webhook receives JSON, extracts user_id
2. **Consent check** → if user not consented, do not store memories
3. **Hybrid memory retrieval** → embed query, compare with Firestore memories, retrieve top-k
4. **Short-term session context** → include session params + buffer
5. **Prompt building & LLM call** → generate response with Vertex AI
6. **Session append & summarization** → if buffer large, summarize + store embedding
7. **Privacy & deletion** → endpoints `/consent` and `/delete_memories`

---

## API Endpoints

- `POST /dialogflow-webhook` → main chatbot interaction
- `POST /consent` → set consent
- `POST /delete_memories` → delete memories

---

## How to Run Locally

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Run server
python main.py
```

### Test Consent

```powershell
$headers = @{ "Content-Type" = "application/json" }
$body = '{"user_id":"testuser","consent":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/consent" -Method POST -Headers $headers -Body $body
```

### Test Chatbot

```powershell
$body = '{
  "session": "projects/genai-bot-kdf/agent/sessions/testsession",
  "messages": [{"text":{"text":["I feel anxious about exams"]}}],
  "sessionInfo": {"parameters": {"user_id": "testuser"}}
}'
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8080/dialogflow-webhook" -Method POST -Headers $headers -Body $body
$response | Format-List *
```

---

## Dialogflow CX Integration

- Add webhook → your Cloud Run / ngrok URL
- Ensure user_id parameter is passed
- Enable webhook call on intents

---

## Deployment (Cloud Run)

```bash
gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot
gcloud run deploy genai-chatbot --image gcr.io/genai-bot-kdf/genai-chatbot --region=asia-south1 --platform=managed --allow-unauthenticated
```

---

## Security & Privacy

- Get user consent
- Store summaries, not raw transcripts
- Crisis handling step needed
- Allow deletion (`/delete_memories`)
- Restrict service account permissions

---

## Troubleshooting

- **ADC error** → set `GOOGLE_APPLICATION_CREDENTIALS`
- **Port in use** → free 8080 or change port
- **Empty reply** → add debug prints, verify model call success
- **Firestore mismatch** → ensure Firestore region correct

---

## Roadmap

- Improve retrieval (Vertex Matching Engine)
- Add UI (React frontend)
- Add tests & monitoring
- Cloud Run deployment with IAM-secured webhook

---

## License

MIT — ensure privacy compliance if handling user data.