# genai-chatbot — Hybrid-memory mental-health chatbot (Vertex AI + Firestore)

**Status:** ✅ fully-functional / deployment-ready

This README documents the whole project: architecture, setup, running, testing, deployment, debugging, privacy/safety, and next steps.

---

## Project Overview

This project is a mental-health-focused chatbot that implements a robust hybrid memory system, powered by Google Cloud's Vertex AI and Firestore.

-   **Short-term memory:** Session parameters and a turn-based buffer (managed in Firestore) provide immediate context for ongoing conversations.
-   **Long-term memory:** Conversation chunks are summarized by a generative model and saved to Firestore with vector embeddings for semantic retrieval.
-   **Hybrid retrieval:** On each new user message, the system performs a vector search to find the most relevant past conversation summaries, prepending them to the prompt for a deeply personalized and continuous user experience.

### Core Components

-   **Flask webhook server:** `main.py` — A robust server with multiple endpoints, compatible with Dialogflow CX or any other webhook-based client.
-   **Vertex AI Generative Models:** Uses the latest Gemini models (e.g., `gemini-1.5-flash`) for intelligent, empathetic responses and conversation summarization.
-   **Vertex AI Embeddings:** Uses `text-embedding-004` to convert text summaries into vectors for semantic search.
-   **Google Cloud Firestore:** A scalable NoSQL database for persistent storage of:
    -   `users` (consent preferences)
    -   `session_buffers` (short-term memory)
    -   `memories` (long-term summarized conversations with embeddings)
-   **Privacy Controls:** A simple consent flow and a dedicated endpoint for users to delete their long-term memories on demand.

---

## File Structure

```
genai-chatbot/
├─ main.py            # Flask webhook, memory logic, and Vertex AI integration
├─ test_chatbot.py    # (Optional) Test script for validating endpoints
├─ requirements.txt   # Python dependencies
├─ README.md          # (This file)
├─ .gitignore
├─ key.json           # Service account key (NEVER commit to Git)
└─ venv/              # Python virtual environment
```

### .gitignore

Ensure your `.gitignore` contains at least the following to protect sensitive information:

```gitignore
.venv/
venv/
__pycache__/
*.pyc
key.json
.env
chatbot.log
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

This project uses the modern, high-level Vertex AI SDK.

```txt
Flask==3.0.3
google-cloud-firestore==2.16.0
google-cloud-aiplatform==1.56.0
numpy==1.26.4
python-dotenv==1.0.1
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

**PowerShell (permanent):**

```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\your\key.json"
```

It is also recommended to set your project and a **working region** (`asia-south1` is confirmed to work well):

```powershell
setx GOOGLE_CLOUD_PROJECT "genai-bot-kdf"
setx REGION "asia-south1"
```

---

## API Endpoints

  - `POST /dialogflow-webhook`: The main endpoint for chatbot interactions.
  - `POST /consent`: Allows a user to grant or deny consent for long-term memory storage.
  - `POST /delete_memories`: Deletes all long-term memories associated with a `user_id`.
  - `GET /health`: A health check endpoint that verifies connectivity to Firestore and Vertex AI services.
  - `GET /debug/models`: A debug endpoint to list available models in your project's region.

---

## How to Run Locally

```powershell
# Activate your virtual environment
.\venv\Scripts\Activate.ps1

# Run the Flask server
python main.py
```

The server will start on `http://127.0.0.1:8080`.

## Testing

This project includes a comprehensive test script (`test_chatbot.py`, if you created one) that validates all endpoints and the core conversation logic.

**To run the tests:**

1.  Make sure the Flask server (`main.py`) is running in one terminal.
2.  In a second terminal, run the test script:
    ```powershell
    python test_chatbot.py
    ```

A successful run will show **`🎉 ALL TESTS PASSED!`** with a `9/9` score.

---

## Deployment (Cloud Run)

You can easily deploy this Flask application as a serverless container on Cloud Run.

```bash
# Submit a build of your container image to Google Container Registry
gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot

# Deploy the container image to Cloud Run
gcloud run deploy genai-chatbot \
  --image gcr.io/genai-bot-kdf/genai-chatbot \
  --region=asia-south1 \
  --platform=managed \
  --allow-unauthenticated
```

*Note: `--allow-unauthenticated` makes the webhook public. For production, secure your webhook using IAM.*

---

## Troubleshooting & Lessons Learned

During development, we encountered several key issues. Here are the solutions:

  - **Symptom:** Health check fails with `ERROR: All models failed` and the bot gives generic error responses.

      - **Cause 1: Incorrect SDK Usage.** The initial problem was using a low-level `gapic` client that was failing silently.
          - **Solution:** Refactor the text generation code to use the modern, high-level `vertexai.generative_models.GenerativeModel` SDK. This is more robust, simpler, and the officially recommended approach for Gemini models.
      - **Cause 2: Incorrect Model Names.** Generative model versions can be deprecated or may not be available in all regions. A specific version like `gemini-1.5-flash-001` might become unavailable.
          - **Solution:** Use **version-less model names** (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`) to always point to the latest stable release. Update all model lists, including in the `health_check` function.

  - **Symptom:** `404 Not Found: Publisher Model ... was not found` error in the server logs.

      - **Cause:** This is a direct confirmation of Cause 2 above. The specific model string you are requesting does not exist in the specified region for your project.
      - **Solution:** Check the [official documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions) for available models and update the names in your code.

  - **Warning:** `ALTS creds ignored. Not running on GCP...` in the server logs.

      - **Cause:** This is a standard, benign warning from the Google Cloud client libraries. It appears when authenticating with a service account key locally instead of on a native GCP environment (like Cloud Run).
      - **Solution:** You can **safely ignore** this message during local development.

---

## Roadmap

  - **Advanced Retrieval:** Integrate **Vertex AI Matching Engine** (formerly Vector Search) for faster and more scalable retrieval of long-term memories.
  - **Frontend UI:** Develop a simple frontend using a framework like React or Vue.js to provide a clean user interface.
  - **CI/CD & Monitoring:** Set up a CI/CD pipeline for automated testing and deployment, and add monitoring/alerting for the production service.
  - **Enhanced Security:** Secure the Cloud Run webhook to only accept requests from authorized sources like Dialogflow using IAM.

---

### Acknowledgements

This project was brought to its final, working state through a fun and collaborative debugging session. A special thanks for the great journey!

---

## License

MIT License — Please ensure you are compliant with all privacy regulations when handling user data.