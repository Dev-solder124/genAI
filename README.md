# genai-chatbot — Intelligent Memory Mental Health Chatbot

**Status:** Fully functional / deployment-ready

A mental health chatbot with intelligent memory powered by Google Cloud Vertex AI and Firestore. Features secure Firebase OAuth authentication, guest sessions, and both command-line interface and modern web frontend.

---

## Database Schema

The application uses a user-centric schema in Google Cloud Firestore with Firebase Authentication for secure user management.

### Firestore Database Structure

The structure is organized around a top-level `users` collection. Each authenticated user's profile and their associated memories are nested under a single user document.

```
users (collection)
└── {sanitized_user_id} (document) - e.g., "user_abc123def"
    |
    ├── profile (map) - Contains the user's metadata
    │   ├── username (string)   - The user's display name from OAuth
    │   ├── email (string)      - User's email from authentication
    │   ├── consent (boolean)   - True if user allows long-term memory storage
    │   ├── created_at (string) - ISO 8601 timestamp of account creation
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

### Authentication Schema

**Firebase Authentication:**
- Supports Google OAuth and anonymous (guest) sessions
- ID tokens used for secure API authentication
- User profiles automatically created on first login

**Memory Document (`users/{user_id}/memories/{memory_id}`)**
- Each document represents significant information the bot has saved
- **summary**: Human-readable text of the conversation
- **embedding**: Numerical representation used to find similar memories
- **metadata**: Additional context like topic classification and session ID

---

## Project Overview

This chatbot implements a sophisticated long-term memory system that intelligently decides what to remember from conversations. Unlike traditional chatbots that either forget everything or save everything, this system curates meaningful memories to provide personalized, continuous mental health support.

### Key Features

- **Firebase OAuth Authentication:** Secure Google sign-in with guest session support
- **Privacy-First Design:** Explicit user consent required before storing any conversations
- **Intelligent Memory:** Only saves conversations with significant therapeutic value, preventing memory clutter
- **Semantic Memory Retrieval:** Uses vector embeddings to find relevant past conversations for context
- **Time-Aware Conversations:** Recognizes time elapsed since last interaction and provides appropriate "welcome back" greetings for natural dialogue flow
- **Dynamic Response Generation:** Explicitly varies phrasing and avoids repetitive opening lines for more engaging, less robotic conversations
- **Multiple Authentication Options:** Google OAuth or anonymous guest sessions
- **Multiple Interfaces:** Secure command-line client and React web frontend
- **User Data Control:** Users can delete all their memories and change consent settings anytime
- **Gemini Integration:** Uses latest Google Gemini models for empathetic responses

### Architecture

- **Authentication:** Firebase Auth with ID token verification
- **Backend:** Flask server with Vertex AI integration and token-based security
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
   - Firebase Authentication enabled with Google OAuth configured
   - Service account with these roles:
     - `Vertex AI User` (roles/aiplatform.user)
     - `Cloud Datastore User` (roles/datastore.user)
     - `Firebase Admin SDK Administrator` (for token verification)
4. **Service account key** downloaded as `service-account-key.json`
5. **Firebase project configuration** for client authentication

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

# Set up authentication (place your service account key in the genAI directory)
# Windows:
$env:GOOGLE_APPLICATION_CREDENTIALS=".\service-account-key.json"
# macOS/Linux:
export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"
```

### 2. Firebase Configuration Setup

Create a `firebase.env` file in your project root with your Firebase project credentials:

```bash
# firebase.env
FIREBASE_API_KEY=your_api_key_here
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

### 3. Running the System

**Option A: Command Line Interface with OAuth**
```bash
# Terminal 1: Start the backend server
python main.py

# Terminal 2: Start the authentication helper (for Google OAuth)
python auth_helper.py

# Terminal 3: Start the CLI chat client
python AuthChat.py
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
├── main.py                        # Flask backend server with OAuth security
├── AuthChat.py                    # OAuth-enabled command-line chat client
├── auth_helper.py                 # Web-based OAuth token generator
├── requirements.txt               # Python dependencies
├── service-account-key.json       # Service account key (add this)
├── firebase.env                   # Firebase project configuration (add this)
├── venv/                          # Python virtual environment
└── genai-frontend/                # React web interface
    ├── package.json
    ├── vite.config.js
    ├── src/
    │   ├── App.jsx
    │   ├── pages/
    │   │   ├── Onboarding.jsx     # User registration
    │   │   ├── Chat.jsx           # Main chat interface
    │   │   ├── Users.jsx          # User management
    │   │   └── Settings.jsx       # User settings
    │   └── lib/
    │       ├── api.js             # Backend API calls
    │       └── storage.js         # Local storage management
    └── ...
```

---

## Environment Setup

### Firebase Authentication Setup

1. **Enable Firebase Authentication** in your Google Cloud/Firebase project
2. **Configure Google OAuth** as a sign-in provider
3. **Download your Firebase config** and create the `firebase.env` file
4. **Enable Anonymous Authentication** for guest sessions (optional)

### Backend Authentication Setup

1. **Download your service account key** from Google Cloud Console
2. **Save the key file** as `service-account-key.json` in the `genAI` directory (same folder as `main.py`)
3. **Set the environment variable** to point to this file:

```bash
# Windows PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS=".\service-account-key.json"

# macOS/Linux Bash  
export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"
```

### Optional Environment Variables

```bash
# Windows PowerShell
$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
$env:REGION="asia-south1"

# macOS/Linux Bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export REGION="asia-south1"
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
firebase-admin==6.2.0
pyrebase4==4.6.0
```

**Frontend:**
- Node.js LTS
- React 18+
- Vite 4+

---

## API Endpoints

All endpoints require valid Firebase ID token authentication (except `/health`):

- `POST /login` - Verify token and create/retrieve user profile
- `POST /dialogflow-webhook` - Main chat endpoint (token required)
- `POST /consent` - User consent management (token required)
- `POST /delete_memories` - Delete user memories (token required)
- `GET /health` - Service health check (no auth required)
- `GET /debug/models` - Available AI models (no auth required)

---

## Usage Instructions

### Command Line Interface with OAuth

1. **Start the backend:** `python main.py`
2. **Start the auth helper:** `python auth_helper.py` 
3. **Start the CLI client:** `python AuthChat.py`
4. **Choose authentication method:**
   - **Google Sign-in:** Follow prompts to authenticate via web browser
   - **Guest Session:** Continue anonymously without persistent memory
5. **Set privacy preferences** (consent for memory storage)
6. **Start chatting** - the bot will remember significant conversations if consented

#### Authentication Flow:
1. CLI prompts for Google sign-in or guest session
2. For Google: Opens web browser at `http://127.0.0.1:5001` for OAuth
3. Copy the provided ID token back to CLI
4. Backend verifies token and creates/retrieves user profile
5. Privacy consent flow begins before chatting

### Web Interface

1. Start the backend: `python main.py`
2. Navigate to `genai-frontend/`
3. Run `npm install` then `npm run dev`
4. Open `http://localhost:5173` in your browser
5. Sign in with Google or continue as guest
6. Complete privacy consent and start chatting

### Frontend-Backend Communication

The web frontend communicates with Flask backend via:
- Vite dev proxy forwards `/api/*` to `http://127.0.0.1:8080`
- Firebase ID tokens for authentication on all API calls
- JSON API calls for all chat operations
- Real-time message exchange through HTTP requests

---

## Authentication Features

### Google OAuth Integration
- Secure sign-in through Firebase Authentication
- Automatic user profile creation from OAuth data
- Persistent sessions across CLI and web interfaces
- Full access to memory storage and retrieval

### Guest Sessions
- Anonymous authentication for privacy-conscious users
- No persistent memory storage (session-only)
- Same chat capabilities without long-term storage
- Easy upgrade to full account if desired

### Security Features
- All API endpoints require valid ID token verification
- User data isolated by authenticated user ID
- Automatic token expiry and refresh handling
- Rate limiting and input validation

---

## Deployment

### Local Development
Both CLI and web interfaces work locally with the Flask development server and proper authentication setup.

### Production (Cloud Run)
```bash
# Build and deploy backend with authentication
gcloud builds submit --tag gcr.io/your-project-id/genai-chatbot
gcloud run deploy genai-chatbot \
  --image gcr.io/your-project-id/genai-chatbot \
  --region=asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-project-id

# Deploy frontend to your preferred static hosting service
cd genai-frontend
npm run build
# Upload dist/ folder to hosting service
```

### Environment Variables for Production
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `REGION`: Your preferred region (default: asia-south1)
- `LLM_MODEL`: AI model to use (default: gemini-1.5-flash)
- Service account should be attached to Cloud Run instance

---

## Troubleshooting

**Authentication Issues:**
- Token verification fails: Check Firebase project configuration and service account permissions
- OAuth flow fails: Verify Google OAuth is enabled in Firebase console
- Guest sessions fail: Enable Anonymous authentication in Firebase

**Backend Issues:**
- Health check fails: Verify Vertex AI API is enabled and credentials are set
- Model errors: Use version-less model names (e.g., `gemini-1.5-flash`)
- Firestore errors: Ensure database is in Native mode and service account has proper permissions

**Frontend Issues:**
- API calls fail: Ensure backend is running on port 8080 with proper CORS setup
- Build errors: Check Node.js version and run `npm install`
- Authentication errors: Verify firebase.env configuration

**Common Warnings:**
- "ALTS creds ignored": Safe to ignore during local development
- Firebase SDK warnings: Usually safe to ignore in development

**CLI-Specific Issues:**
- "firebase.env not found": Create the file with your Firebase project configuration
- "pyrebase4 errors": Ensure all Firebase settings are correctly configured
- Token paste issues: Copy the entire token from the web browser carefully

---

## Privacy & Security

### Data Protection
- **Explicit consent required** before storing any conversation memories
- **Conversations are summarized**, not stored verbatim for privacy
- **Users can delete all their data** at any time via API
- **Anonymous guest sessions** available for maximum privacy

### Security Measures
- **Firebase ID token verification** on all protected endpoints
- **User data isolation** - users can only access their own data
- **Service account minimal permissions** - only required GCP roles
- **Input validation and sanitization** on all user inputs
- **Rate limiting** to prevent abuse

### Compliance Considerations
- GDPR-compliant data deletion capabilities
- User consent tracking and management
- Audit trails for data access and modifications
- Minimal data retention policies

---

## License

MIT License - Ensure compliance with privacy regulations when handling user data. This application handles personal conversations and requires appropriate privacy safeguards in production environments.