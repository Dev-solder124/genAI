# genai-chatbot — Intelligent Memory Mental Health Chatbot

**Status:** Fully functional / deployment-ready with Vertex AI Vector Search

A mental health chatbot with intelligent memory powered by Google Cloud Vertex AI Vector Search, providing scalable, high-performance semantic memory retrieval. The system stores encrypted conversation summaries in Firestore while leveraging Vertex AI's dedicated vector search infrastructure for lightning-fast similarity matching. Features end-to-end encryption for sensitive data using Google Cloud KMS, secure Firebase OAuth authentication, guest sessions, dynamic time-aware conversations, and both command-line interface and modern web frontend.

## Project Overview

### Existing Gap in Chatbots for Mental Health Support

Traditional chatbots either forget everything after each session or store everything indiscriminately, leading to irrelevant responses or privacy concerns. Those that do implement memory typically use inefficient full-database scans for each query, resulting in poor performance and scalability issues. Additionally, most mental health chatbots store sensitive conversation data in plaintext, creating significant security and compliance risks.

### Solution Offered

This chatbot implements a production-grade, scalable memory architecture that combines:

- Intelligent curation of meaningful therapeutic conversations
- Vertex AI Vector Search for high-performance semantic retrieval
- End-to-end encryption using Google Cloud KMS for HIPAA-grade security
- User-specific namespace filtering ensuring complete privacy isolation between users
- Temporal awareness for contextually appropriate responses

The result is a chatbot that provides personalized, continuous mental health support with enterprise-level performance and security.

## Key Features

### 1. Advanced Memory Architecture

- **Vertex AI Vector Search Integration:** Dedicated, scalable vector search infrastructure
- **O(log n) Performance:** Sub-100ms memory retrieval regardless of database size
- **User Namespace Isolation:** Each user's vectors are isolated in their own namespace
- **Automatic Failover:** Gracefully handles Vector Search unavailability
- **Hybrid Storage:** Encrypted metadata in Firestore, vectors in Vector Search

### 2. Access and Authentication

- **Firebase OAuth Authentication:** Secure Google sign-in with guest session support
- **Multiple Authentication Options:** Google OAuth or anonymous guest sessions

### 3. Privacy and User Control

- **Privacy-First Design:** Explicit user consent required before storing any conversations
- **User Data Control:** Users can delete all their memories and change consent settings anytime
- **End-to-End Encryption:** All sensitive data encrypted at rest using Google Cloud KMS
- **HIPAA-Grade Security:** Enterprise-level encryption for mental health data protection
- **Complete User Isolation:** Users can only access their own memories via namespace filtering

### 4. Intelligent Memory System

- **Intelligent Memory:** Only saves conversations with significant therapeutic value, preventing memory clutter
- **Semantic Memory Retrieval:** Uses 768-dimensional vector embeddings (text-embedding-004) for accurate similarity matching
- **Encrypted Storage:** Conversation summaries and PII are encrypted before storage
- **Plaintext Processing:** Vector embeddings generated from plaintext for accurate similarity matching
- **Granular Memory Timestamps:** Each retrieved memory includes precise temporal context (e.g., "2 days ago", "5 minutes ago")
- **Temporal Conversation Flow:** Recognizes time patterns and provides contextually appropriate responses

### 5. Security Architecture

- **Cloud KMS Integration:** Military-grade encryption using Google Cloud Key Management Service
- **Selective Encryption:** Only sensitive fields encrypted (summaries, names, emails)
- **Performance Optimized:** Embeddings stored in Vector Search for fast semantic search
- **Automatic Decryption:** Transparent decryption during memory retrieval
- **Key Rotation Support:** Compatible with KMS key rotation policies

### 6. Dynamic Conversation Experience

- **Dynamic Time-Aware Greetings:** Automatically adapts opening messages based on actual time elapsed since last interaction
- **Dynamic Response Generation:** Explicitly varies phrasing and avoids repetitive opening lines
- **Context-Aware Responses:** Seamlessly integrates relevant past memories into conversations

### 7. Interfaces and Integration

- **Multiple Interfaces:** Secure command-line client and React web frontend
- **Gemini Integration:** Uses latest Google Gemini 2.5 Flash model for empathetic responses

## High Level Architecture Flow

```
User Input
    ↓
[1. Generate Embedding] (text-embedding-004, 768 dimensions)
    ↓
[2. Query Vector Search] (with user namespace filter)
    ↓ (returns memory IDs + similarity scores)
    ↓
[3. Hydrate from Firestore] (batch get encrypted summaries)
    ↓
[4. Decrypt Summaries] (Google Cloud KMS)
    ↓
[5. Generate AI Response] (Gemini 2.5 Flash with context)
    ↓
[6. Analyze Conversation] (determine if significant)
    ↓
[7. If Significant:]
    ├─ Encrypt Summary (KMS)
    ├─ Store Metadata (Firestore)
    └─ Upsert Vector (Vector Search with user namespace)
    ↓
Response to User
```

## Detailed Component Flow

### Memory Storage (Write Path)

1. User sends message → AI generates response
2. Conversation analyzed for significance
3. If significant:
   - Generate embedding from plaintext summary (768-dim vector)
   - Encrypt summary using Cloud KMS
   - Save encrypted summary + metadata to Firestore
   - Upsert vector to Vertex AI Vector Search with user namespace restriction
   - Memory ID links Firestore document to Vector Search datapoint

### Memory Retrieval (Read Path)

1. User sends new message
2. Generate query embedding (768-dim vector)
3. Query Vertex AI Vector Search with user namespace filter
4. Receive top-k similar memory IDs and distances
5. Batch-fetch corresponding documents from Firestore
6. Decrypt summaries using Cloud KMS
7. Add temporal context ("2 days ago")
8. Include in AI prompt for contextual response

### Privacy Isolation

- Each vector stored with user_id namespace restriction
- Queries filtered to only search within user's namespace
- Impossible for User A to retrieve User B's memories
- Double-protected: Firestore subcollections + Vector Search namespaces

## Architecture

## Technology Stack

- **Authentication:** Firebase Auth with ID token verification
- **Backend:** Flask server with Vertex AI integration and token-based security
- **Database (Metadata):** Google Cloud Firestore for user profiles and encrypted memory summaries
- **Vector Search:** Vertex AI Vector Search for high-performance semantic similarity
- **Encryption:** Google Cloud KMS for at-rest encryption of sensitive data
- **AI Models:**
  - Gemini 2.5 Flash for conversations
  - text-embedding-004 for 768-dimensional memory vectors
- **Frontend:** React + Vite web interface

## Why Vector Search?

The project leverages Vertex AI Vector Search for its high-performance, scalable architecture:

- Vectors are stored in dedicated, optimized Vector Search infrastructure.
- It uses approximate nearest neighbor (ANN) algorithms, providing O(log n) query complexity.
- Similarity computation is hardware-accelerated.
- Performance remains constant (typically 50-200ms) regardless of the total memory count.
- This architecture also provides storage cost reduction by not storing large embedding arrays in Firestore.

## Database Schema

The application uses a hybrid storage architecture combining Firestore and Vertex AI Vector Search.

### Firestore Structure (Encrypted Metadata)

```
users (collection)
└── {sanitized_user_id} (document) - e.g., "user_abc123def"
    |
    ├── profile (map) - Contains the user's metadata
    │   ├── username (string) 🔒 ENCRYPTED
    │   ├── username_encrypted (boolean)
    │   ├── email (string) 🔒 ENCRYPTED
    │   ├── email_encrypted (boolean)
    │   ├── consent (boolean) - Memory storage permission
    │   ├── is_anonymous (boolean)
    │   ├── created_at (string) - ISO 8601 timestamp
    │   └── updated_at (string) - ISO 8601 timestamp (last interaction)
    |
    └── memories (sub-collection) - Encrypted summaries only
        |
        └── {memory_id} (document) - e.g., "mem_1758..."
            ├── user_id (string)
            ├── summary (string) 🔒 ENCRYPTED
            ├── summary_encrypted (boolean)
            ├── metadata (map) - {"topic": "...", "session_id": "..."}
            └── created_at (string) - ISO 8601 timestamp
            
            ❌ embedding array REMOVED (now in Vector Search)
```

🔒 = Encrypted at rest using Google Cloud KMS

### Vertex AI Vector Search Structure (Vectors)

```
Vector Search Index: "chatbot-memory-index"
├── Dimensions: 768 (text-embedding-004)
├── Distance Measure: Dot Product
└── Algorithm: Tree-AH (approximate nearest neighbors)

Datapoints:
└── {memory_id} (e.g., "mem_1758...")
    ├── datapoint_id: mem_1758... (links to Firestore)
    ├── feature_vector: [0.123, -0.456, ...] (768 dimensions)
    └── restricts: [
        {
            namespace: "user_id",
            allow_list: ["user_abc123def"]
        }
    ]
```

🔐 = User namespace isolation ensures privacy

## Data Flow

- **Write:** Firestore document created → Vector upserted to Vector Search (with namespace)
- **Read:** Vector Search query → Returns memory IDs → Firestore batch fetch → Decrypt
- **Delete:** Firestore documents deleted → Vectors removed from Vector Search

## Encryption Strategy

### What Gets Encrypted (Firestore)
- User profile PII (username, email)
- Conversation summaries stored in memories
- Any personally identifiable information

### What Stays Unencrypted
- Vector embeddings (stored in Vector Search, not human-readable)
- Timestamps (needed for temporal processing)
- User IDs (already pseudonymized Firebase UIDs)
- Boolean flags (consent, anonymous status)
- Metadata tags

### Why This Approach
- Embeddings must be generated from plaintext to ensure accurate similarity matching. The workflow is:
  - Generate embedding from plaintext summary
  - Encrypt the summary text
  - Store encrypted summary in Firestore (without embedding)
  - Store vector in Vector Search with user namespace
  - During retrieval: Query Vector Search → Get memory IDs → Fetch from Firestore → Decrypt summaries
- This ensures security (encrypted storage), privacy (namespace isolation), and performance (fast vector search).

## Prerequisites

- Python 3.11 installed
- Node.js (LTS version)
- Google Cloud Project with:
  - Vertex AI API enabled
  - Vertex AI Vector Search (index + endpoint deployed)
  - Firestore database (Native mode)
  - Firebase Authentication (Google OAuth configured)
  - Cloud KMS API (for encryption)
  - Service account with roles:
    - Vertex AI User (roles/aiplatform.user)
    - Cloud Datastore User (roles/datastore.user)
    - Firebase Admin SDK Administrator
    - Cloud KMS CryptoKey Encrypter/Decrypter
  - Service account key (for local development only)
  - Firebase project configuration
  - KMS key ring and encryption key
- Vector Search Infrastructure:
  - Vector Search Index created (768 dimensions, Dot Product similarity)
  - Index Endpoint deployed
  - Deployed Index ID noted

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

# Set up authentication (local development only)
# Windows:
$env:GOOGLE_APPLICATION_CREDENTIALS=".\service-account-key.json"
# macOS/Linux:
export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"
```

### 2. Firebase Configuration Setup

Create a firebase.env file in your project root:

```bash
# firebase.env
FIREBASE_API_KEY=your_api_key_here
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

### 3. Encryption Setup (Cloud KMS)

```bash
# Enable Cloud KMS API
gcloud services enable cloudkms.googleapis.com --project=your-project-id

# Create key ring (one-time setup)
gcloud kms keyrings create chatbot-encryption \
    --location=asia-south1 \
    --project=your-project-id

# Create encryption key
gcloud kms keys create memory-encryption-key \
    --location=asia-south1 \
    --keyring=chatbot-encryption \
    --purpose=encryption \
    --project=your-project-id

# Grant permissions
gcloud kms keys add-iam-policy-binding memory-encryption-key \
    --location=asia-south1 \
    --keyring=chatbot-encryption \
    --member="serviceAccount:your-service-account@your-project.iam.gserviceaccount.com" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" \
    --project=your-project-id
```

### 4. Vector Search Setup

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=your-project-id

# Note: Vector Search Index and Endpoint must be created via Cloud Console
# See "Vector Search Configuration" section below
```

### 5. Environment Variables

Set these environment variables for your application:

```bash
# Required
export GOOGLE_CLOUD_PROJECT="your-project-id"
export REGION="asia-south1"

# Vector Search Configuration (get these from Cloud Console)
export VECTOR_SEARCH_ENDPOINT_ID="projects/PROJECT_NUM/locations/REGION/indexEndpoints/ENDPOINT_ID"
export DEPLOYED_INDEX_ID="your-deployed-index-id"
export VECTOR_SEARCH_INDEX_ID="your-index-id"

# Optional
export LLM_MODEL="gemini-2.5-flash"
export EMBEDDING_MODEL="text-embedding-004"
```

### 6. Running the System

#### Option A: Command Line Interface

```bash
# Terminal 1: Start backend
python main.py

# Terminal 2: Start auth helper
python auth_helper.py

# Terminal 3: Start CLI client
python AuthChat.py
```

#### Option B: Web Interface

```bash
# Terminal 1: Start backend
python main.py

# Terminal 2: Start frontend
cd genai-frontend
npm install
npm run dev

Open browser to http://localhost:5173
```

## Vector Search Configuration

### Creating the Vector Search Infrastructure

1. **Create Vector Search Index (via Cloud Console):**
   - Go to: Vertex AI → Vector Search → Indexes
   - Click "Create Index"
   - Display name: chatbot-memory-index
   - Region: asia-south1
   - Dimensions: 768 ⚠️ CRITICAL (must match text-embedding-004)
   - Distance measure: Dot Product
   - Update method: Streaming updates
   - Algorithm: Tree-AH
2. **Create Index Endpoint (via Cloud Console):**
   - Go to: Vertex AI → Vector Search → Index Endpoints
   - Click "Create Endpoint"
   - Display name: chatbot-memory-endpoint
   - Region: asia-south1
3. **Deploy Index to Endpoint:**
   - Select your endpoint
   - Click "Deploy Index"
   - Select your index
   - Deployed index ID: serena_memory_deployed (or your choice)
   - Machine type: e2-standard-2
   - Min replicas: 1
   - Max replicas: 2
4. **Note Your Configuration:**
   - After deployment, note these values for your environment variables:
     - VECTOR_SEARCH_ENDPOINT_ID: Full endpoint resource name
     - DEPLOYED_INDEX_ID: The deployed index ID you chose
     - VECTOR_SEARCH_INDEX_ID: Your index ID

## File Structure

```
genAI/
├── main.py                        # Flask backend with Vector Search integration
├── encryption.py                  # KMS encryption/decryption service
├── AuthChat.py                    # OAuth-enabled CLI client
├── auth_helper.py                 # Web-based OAuth token generator
├── requirements.txt               # Python dependencies
├── service-account-key.json       # Service account key (local dev only)
├── firebase.env                   # Firebase configuration
├── venv/                          # Python virtual environment
└── genai-frontend/                # React web interface
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── pages/
        │   ├── Onboarding.jsx
        │   ├── Chat.jsx
        │   ├── Users.jsx
        │   └── Settings.jsx
        └── lib/
            ├── api.js
            └── storage.js
```

## API Endpoints

All endpoints require Firebase ID token authentication (except /health):

### Public Endpoints

- `GET /health` - Service health check (includes Vector Search status)

### Authenticated Endpoints

- `POST /login` - Verify token and create/retrieve encrypted user profile
- `POST /dialogflow-webhook` - Main chat endpoint with Vector Search retrieval
- `POST /consent` - User consent management
- `POST /delete_memories` - Delete from both Firestore and Vector Search

#### Endpoint Details

- `POST /dialogflow-webhook` - Core Conversation Flow:
  - Receives user message
  - Queries Vector Search with user namespace filter
  - Hydrates memory metadata from Firestore
  - Decrypts summaries
  - Generates AI response with context
  - Analyzes conversation significance
  - If significant: encrypts, stores in Firestore, upserts to Vector Search
- `POST /delete_memories` - Complete Data Removal:
  - Retrieves all memory IDs from Firestore
  - Deletes vectors from Vector Search (by datapoint IDs)
  - Batch-deletes documents from Firestore
  - Returns deletion count

## Usage Instructions

### Command Line Interface

- Start backend: `python main.py`
- Start auth helper: `python auth_helper.py`
- Start CLI: `python AuthChat.py`
- Choose Google sign-in or guest session
- Set privacy preferences
- Start chatting - memories retrieved via Vector Search

### Web Interface

- Start backend: `python main.py`
- Navigate to genai-frontend/
- Run `npm install` then `npm run dev`
- Open http://localhost:5173
- Sign in with Google or continue as guest
- Complete consent and start chatting
- Experience fast, context-aware responses powered by Vector Search

## How Memory Works

### User Perspective

- Chat naturally with Serena
- Significant conversations are automatically remembered
- Previous context seamlessly integrated into responses
- Time-aware greetings ("Welcome back, it's been 3 days...")
- Instant responses regardless of conversation history length

### Technical Perspective

- Every message triggers Vector Search query (50-200ms)
- Top 3 most similar memories retrieved
- Memories decrypted and added to AI prompt
- Response generated with full context
- New significant exchanges automatically saved

## Deployment

### Local Development

Both CLI and web interfaces work locally with:

- Flask development server
- Vector Search integration (if configured)
- Full encryption capabilities (if KMS configured)
- Automatic failover to Firestore if Vector Search unavailable

### Production (Cloud Run)

```bash
# Build container
gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot

# Deploy with Vector Search configuration
gcloud run deploy genai-chatbot \
  --image gcr.io/genai-bot-kdf/genai-chatbot \
  --region=asia-south1 \
  --allow-unauthenticated \
  --platform managed \
  --service-account=firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=genai-bot-kdf,\
REGION=asia-south1,\
VECTOR_SEARCH_ENDPOINT_ID=projects/922976482476/locations/asia-south1/indexEndpoints/2041203754547544064,\
DEPLOYED_INDEX_ID=serena_memory_deployed,\
VECTOR_SEARCH_INDEX_ID=your-index-id

# Deploy frontend
cd genai-frontend
npm run build
firebase deploy --only hosting
```

### Environment Variables for Production

Required environment variables in Cloud Run:

- GOOGLE_CLOUD_PROJECT: Your GCP project ID
- REGION: asia-south1
- VECTOR_SEARCH_ENDPOINT_ID: Full endpoint resource name
- DEPLOYED_INDEX_ID: Your deployed index ID
- VECTOR_SEARCH_INDEX_ID: Your index ID
- LLM_MODEL: gemini-2.5-flash (optional, has default)
- EMBEDDING_MODEL: text-embedding-004 (optional, has default)

## Security & Compliance

### Encryption Details

- **Encryption Standard:**
  - Algorithm: AES-256-GCM (Google Cloud KMS)
  - Key Management: Google Cloud Key Management Service
  - Key Storage: Hardware Security Modules (HSMs)
  - Key Rotation: Automatic via KMS
- **Data Classification:**
  - Encrypted at Rest: User profiles, conversation summaries (Firestore)
  - Not Encrypted: Vector embeddings (mathematical representations, not human-readable)
  - Encrypted in Transit: All API calls use HTTPS/TLS 1.3
  - Never Stored: Raw chat messages
- **Privacy Isolation:**
  - Each user's vectors tagged with unique namespace
  - Query filters prevent cross-user data access
  - Double-protected: Firestore subcollections + Vector Search namespaces
  - Impossible for User A to access User B's memories

### Compliance

- HIPAA-ready architecture (requires BAA with Google Cloud)
- GDPR-compliant data handling
- Right to erasure via /delete_memories endpoint
- Explicit consent management
- Audit logging via Cloud Console

### Best Practices

- Never commit service-account-key.json to version control
- Use environment variables for all sensitive configuration
- Enable audit logging for KMS and Vector Search operations
- Regular key rotation via Cloud KMS
- Monitor Vector Search performance metrics
- Backup Firestore before major changes

## License

MIT License - Ensure compliance with privacy regulations when handling user data. This application handles encrypted personal mental health conversations with high-performance vector search and requires appropriate privacy safeguards, security audits, and compliance verification in production environments.

**Security Note:** While this implementation provides strong encryption at rest and complete user isolation via namespaces, full HIPAA compliance requires additional measures including Business Associate Agreements (BAA) with Google Cloud, comprehensive audit logging, access controls, and regular security assessments. Consult with legal and security professionals before handling Protected Health Information (PHI).
