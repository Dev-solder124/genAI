# genai-chatbot — Intelligent Memory Mental Health Chatbot

**Status:** Fully functional / deployment-ready

A mental health chatbot with intelligent memory powered by Google Cloud Vertex AI and Firestore. Features both a command-line interface and a modern web frontend.

---

## Database Schema

The application uses a user-centric schema in Google Cloud Firestore.

### Firestore Database Structure

The structure is organized around a top-level `users` collection. Each user's profile and their associated memories are nested under a single user document.

```
users (collection)
└── {user_id} (document) - e.g., "user_1092"
    |
    ├── profile (map) - Contains the user's metadata
    │   ├── username (string)   - The user's chosen display name, e.g., "devesh"
    │   ├── consent (boolean)   - True if user allows long-term memory storage
    │   └── updated_at (string) - ISO 8601 timestamp of last profile update
    │
    └── memories (sub-collection) - Contains all significant memories for this user
        |
        └── {memory_id} (document) - e.g., "mem_1758..."
            ├── user_id (string)    - The ID of the user who owns this memory
            ├── summary (string)    - AI-generated summary of the conversation
            ├── embedding (array)   - Vector embedding of summary for semantic search
            ├── metadata (map)      - Extra context, e.g., {"topic": "...", "session_id": "..."}
            └── created_at (string) - ISO 8601 timestamp when memory was created
```

### Schema Details

**User Document (`users/{user_id}`)**
- Central document for each user containing profile information
- Contains a `memories` sub-collection for conversation history

**Memory Document (`users/{user_id}/memories/{memory_id}`)**
- Each document represents significant information the bot has saved
- **summary**: Human-readable text of the conversation
- **embedding**: Numerical representation used to find similar memories
- **metadata**: Additional context like topic classification and session ID

---

## Project Overview

This chatbot implements a sophisticated long-term memory system that intelligently decides what to remember from conversations. Unlike traditional chatbots that either forget everything or save everything, this system curates meaningful memories to provide personalized, continuous mental health support.

### Key Features

- **Intelligent Memory:** Only saves conversations with significant therapeutic value, preventing memory clutter
- **Semantic Memory Retrieval:** Uses vector embeddings to find relevant past conversations for context
- **Multiple Interfaces:** Command-line client and React web frontend
- **Privacy-First:** User consent required, with ability to delete all memories
- **Gemini Integration:** Uses latest Google Gemini models for empathetic responses

### Architecture

- **Backend:** Flask server with Vertex AI integration
- **Database:** Google Cloud Firestore for user profiles and memories  
- **AI Models:** Gemini 1.5 Flash for conversations, text-embedding-004 for memory vectors
- **Frontend:** React + Vite web interface (optional)

---

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.11** installed
2. **Node.js** (LTS version) for the web frontend
3. **Google Cloud Project** with:
   - Vertex AI API enabled
   - Firestore database created (Native mode)
   - Service account with these roles:
     - `Vertex AI User` (roles/aiplatform.user)
     - `Cloud Datastore User` (roles/datastore.user)
4. **Service account key** downloaded as `key.json`

---

## Quick Start

### 1. Backend Setup

```bash
# Clone/download the project and navigate to it
cd genAI

# Create Python 3.11 virtual environment
python3.11 -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set up authentication (place your key.json file in the genAI directory)
# Windows:
$env:GOOGLE_APPLICATION_CREDENTIALS=".\key.json"
# macOS/Linux:
export GOOGLE_APPLICATION_CREDENTIALS="./key.json"
```

### 2. Running the System

**Option A: Command Line Interface**
```bash
# Terminal 1: Start the backend server
python main.py

# Terminal 2: Start the CLI chat client
python chat.py
```

**Option B: Web Interface**
```bash
# Terminal 1: Start the backend server
python main.py

# Terminal 2: Start the web frontend
cd genai-frontend
npm install
npm run dev
```

Then open your browser to `http://localhost:5173`

---

## File Structure

```
genAI/
├── main.py                    # Flask backend server
├── chat.py                    # Command-line chat client
├── requirements.txt           # Python dependencies
├── key.json                   # Service account key (add this)
├── venv/                      # Python virtual environment
└── genai-frontend/            # React web interface
    ├── package.json
    ├── vite.config.js
    ├── src/
    │   ├── App.jsx
    │   ├── pages/
    │   │   ├── Onboarding.jsx # User registration
    │   │   ├── Chat.jsx       # Main chat interface
    │   │   ├── Users.jsx      # User management
    │   │   └── Settings.jsx   # User settings
    │   └── lib/
    │       ├── api.js         # Backend API calls
    │       └── storage.js     # Local storage management
    └── ...
```

---

## Environment Setup

### Authentication Setup

1. **Download your service account key** from Google Cloud Console
2. **Save the key file** as `key.json` in the `genAI` directory (same folder as `main.py`)
3. **Set the environment variable** to point to this file:

```bash
# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS=".\key.json"

# macOS/Linux Bash  
export GOOGLE_APPLICATION_CREDENTIALS="./key.json"
```

### Optional Environment Variables

```bash
# Windows PowerShell
setx GOOGLE_CLOUD_PROJECT "your-gcp-project-id"

# macOS/Linux Bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
```

### Dependencies

**Backend (requirements.txt):**
```txt
Flask==2.3.2
google-cloud-firestore==2.11.0
google-cloud-aiplatform>=1.26.0
numpy==1.26.0
python-dotenv==1.0.0
requests==2.31.0
```

**Frontend:**
- Node.js LTS
- React 18+
- Vite 4+

---

## API Endpoints

- `POST /dialogflow-webhook` - Main chat endpoint
- `POST /consent` - User consent management
- `POST /delete_memories` - Delete user memories
- `GET /health` - Service health check
- `GET /debug/models` - Available AI models

---

## Usage Instructions

### Command Line Interface

1. Start the backend: `python main.py`
2. In another terminal: `python chat.py`
3. Choose a user ID when prompted
4. Give consent for memory storage
5. Start chatting - the bot will remember significant conversations

### Web Interface

1. Start the backend: `python main.py`
2. Navigate to `genai-frontend/`
3. Run `npm install` then `npm run dev`
4. Open `http://localhost:5173` in your browser
5. Complete onboarding and start chatting

### Frontend-Backend Communication

The web frontend communicates with Flask backend via:
- Vite dev proxy forwards `/api/*` to `http://127.0.0.1:8080`
- JSON API calls for all chat operations
- Real-time message exchange through HTTP requests

---

## Deployment

### Local Development
Both interfaces work locally with the Flask development server.

### Production (Cloud Run)
```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/your-project-id/genai-chatbot
gcloud run deploy genai-chatbot \
  --image gcr.io/your-project-id/genai-chatbot \
  --region=asia-south1 \
  --allow-unauthenticated

# Deploy frontend to your preferred static hosting service
cd genai-frontend
npm run build
# Upload dist/ folder to hosting service
```

---

## Troubleshooting

**Backend Issues:**
- Health check fails: Verify Vertex AI API is enabled and credentials are set
- Model errors: Use version-less model names (e.g., `gemini-1.5-flash`)
- Firestore errors: Ensure database is in Native mode

**Frontend Issues:**
- API calls fail: Ensure backend is running on port 8080
- Build errors: Check Node.js version and run `npm install`

**Common Warnings:**
- "ALTS creds ignored": Safe to ignore during local development

---

## Privacy & Security

- User consent required before storing any memories
- Conversations are summarized, not stored verbatim
- Users can delete all their data at any time
- Service account should have minimal required permissions

---

## License

MIT License - Ensure compliance with privacy regulations when handling user data.