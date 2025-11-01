# GenAI Chatbot - Production & Deployment Guide

**Status:** Updated for Vector Search & KMS Integration

This document provides all the necessary steps to deploy and maintain the GenAI Chatbot application. The application consists of a Python (Flask) backend running on **Google Cloud Run** and a React frontend hosted on **Firebase Hosting**. It now utilizes **Vertex AI Vector Search** for memory retrieval and **Google Cloud KMS** for encryption.

## 1. Cloud Prerequisites (One-Time Setup)

Before deploying, ensure your Google Cloud project is configured correctly:

1.  **Enable Required APIs:**
    ```bash
    gcloud services enable \
        run.googleapis.com \
        build.googleapis.com \
        iam.googleapis.com \
        firestore.googleapis.com \
        aiplatform.googleapis.com \
        cloudkms.googleapis.com \
        firebase.googleapis.com \
        --project=genai-bot-kdf
    ```
2.  **Configure Firestore:** Ensure Firestore is enabled in **Native mode**.
3.  **Configure Firebase Authentication:** Enable desired providers (e.g., Google, Anonymous).
4.  **Create KMS Key Ring and Key:** (If not already done)
    ```bash
    # Create key ring (replace region if needed)
    gcloud kms keyrings create chatbot-encryption \
        --location=asia-south1 \
        --project=genai-bot-kdf

    # Create encryption key
    gcloud kms keys create memory-encryption-key \
        --location=asia-south1 \
        --keyring=chatbot-encryption \
        --purpose=encryption \
        --project=genai-bot-kdf
    ```
5.  **Configure Service Account IAM Roles:** Ensure your service account (`firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com`) has the following roles:
    * `Cloud Run Invoker` (To allow Firebase Hosting to call Cloud Run)
    * `Service Account User` (For Cloud Run to act as the service account)
    * `Vertex AI User` (To call Embedding, LLM, and Vector Search APIs)
    * `Cloud Datastore User` (To access Firestore)
    * `Firebase Admin SDK Administrator` (or `Firebase Admin` for token verification)
    * `Cloud KMS CryptoKey Encrypter/Decrypter` (To encrypt/decrypt data)

    You can grant roles using `gcloud projects add-iam-policy-binding` or via the Cloud Console (IAM & Admin -> IAM). Example for KMS role:
    ```bash
    gcloud kms keys add-iam-policy-binding memory-encryption-key \
        --location=asia-south1 \
        --keyring=chatbot-encryption \
        --member="serviceAccount:firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com" \
        --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" \
        --project=genai-bot-kdf
    ```
6.  **Set up Vertex AI Vector Search:** (If not already done)
    * Create a Vector Search Index (e.g., `serenachat-memory-index`, 768 dimensions, Dot Product Distance, Stream Update).
    * Create and deploy the Index to a Public Endpoint (e.g., `serenachat-memory-endpoint`).
    * Note the **numerical Endpoint ID** (e.g., `2041203754547544064`) and the **Deployed Index ID** (e.g., `serena_memory_deployed`).

---

## 2. Local Development Tools Setup
Ensure you have the following tools installed and configured:

-   **Git:** For cloning the repository.
-   **Google Cloud CLI (`gcloud`):** [Installation Guide](https://cloud.google.com/sdk/docs/install)
-   **Firebase Tools (`firebase`):** Install via npm: `npm install -g firebase-tools`
-   **Node.js (LTS):** For managing the frontend application.
-   **Python 3.11+ & Pip:** For the backend.

---

## 3. Initial Deployment (From a Fresh Start)
Follow these steps to deploy the entire application from scratch.

### ### Phase A: Local Code Setup
1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/Dev-solder124/genAI.git](https://github.com/Dev-solder124/genAI.git)
    cd genAI
    ```
2.  **(Optional) Add Service Account Key for Local Testing:**
    Download your `service-account-key.json` file. Place it in the root `genAI/` directory. **Do not commit this file.** Set the environment variable for local testing:
    ```bash
    # Windows PowerShell
    $env:GOOGLE_APPLICATION_CREDENTIALS=".\service-account-key.json"
    # macOS/Linux Bash
    export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"
    ```
3.  **Configure Cloud Tools:**
    Log in and select your project.
    ```bash
    gcloud init
    firebase login
    gcloud config set project genai-bot-kdf
    firebase use genai-bot-kdf
    ```
### ### Phase B: Deploy the Backend
All commands should be run from the root `genAI/` directory.

1.  **Install Backend Dependencies (Locally):**
    ```bash
    # Create and activate a virtual environment (recommended)
    python3 -m venv venv
    source venv/bin/activate # or .\venv\Scripts\Activate.ps1 on Windows
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
2.  **Build the Container Image:**
    This command packages your Python application into a Docker container.
    ```bash
    gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot --project=genai-bot-kdf
    ```
3.  **Deploy to Cloud Run with Environment Variables:**
    This launches the container and sets the required variables. **Replace placeholders if your IDs/names differ.**
    ```gcloud run deploy genai-chatbot \
  --image gcr.io/genai-bot-kdf/genai-chatbot \
  --region=asia-south1 \
  --project=genai-bot-kdf \
  --platform managed \
  --allow-unauthenticated \
  --service-account="firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com" \
  --set-env-vars=VECTOR_SEARCH_ENDPOINT_ID=projects/922976482476/locations/asia-south1/indexEndpoints/2041203754547544064,VECTOR_SEARCH_INDEX_ID=8641572056086872064,DEPLOYED_INDEX_ID=serena_memory_deployed,GOOGLE_CLOUD_PROJECT=genai-bot-kdf,REGION=asia-south1,KMS_LOCATION=asia-south1,KMS_KEYRING=chatbot-encryption,KMS_KEY=memory-encryption-key
    ```
    After this step, you will receive a **Service URL** (e.g., `https://genai-chatbot-....run.app`). **Copy this URL.**

### ### Phase C: Deploy the Frontend
1.  **Navigate to the Frontend Directory:**
    ```bash
    cd genai-frontend
    ```
2.  **Create Production Environment File:**
    Create a new file named `.env.production`. Paste the following content, replacing the backend URL and adding your **public** Firebase web keys (found in Firebase Console -> Project Settings -> General -> Your apps -> Web app -> SDK setup and configuration -> Config).
    ```dotenv
    # Backend URL from the previous step
    VITE_API_BASE_URL=[https://genai-chatbot-....a.run.app](https://genai-chatbot-....a.run.app) # PASTE YOUR CLOUD RUN URL HERE

    # Your public Firebase keys
    VITE_FIREBASE_API_KEY=AIzaSy...
    VITE_FIREBASE_AUTH_DOMAIN=genai-bot-kdf.firebaseapp.com
    VITE_FIREBASE_PROJECT_ID=genai-bot-kdf
    VITE_FIREBASE_STORAGE_BUCKET=genai-bot-kdf.appspot.com
    VITE_FIREBASE_MESSAGING_SENDER_ID=9... # Your Sender ID
    VITE_FIREBASE_APP_ID=1:9... # Your App ID
    ```
3.  **Install Dependencies:**
    ```bash
    npm install
    ```
4.  **Initialize Firebase Hosting (One-Time):**
    If you haven't done this before for this directory:
    ```bash
    firebase init hosting
    ```
    * Select **Use an existing project** (`genai-bot-kdf`).
    * For the public directory, enter **`dist`**.
    * Configure as a single-page app: **`Yes`**.
    * Set up automatic builds with GitHub: **`No`**.

5.  **Build and Deploy:**
    ```bash
    npm run build
    firebase deploy --only hosting
    ```
    After this step, you will receive a **Hosting URL** (e.g., `https://genai-bot-kdf.web.app`). This is your live application.

---

## 4. How to Update the Application
Once deployed, follow these steps to update.

### ### How to Update the Backend
To make changes to your Python code (e.g., update a prompt in `main.py`).

1.  **Make your code changes** and save the files in the `genAI/` directory.
2.  **Ensure `requirements.txt` is up-to-date** if you added new libraries.
3.  From the root `genAI/` directory, run the **build** and **deploy** commands again:
    ```bash
    # Step 1: Re-build the container with your changes
    gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot --project=genai-bot-kdf

    # Step 2: Re-deploy the new container version with all environment variables
    gcloud run deploy genai-chatbot --image gcr.io/genai-bot-kdf/genai-chatbot --region=asia-south1 --project=genai-bot-kdf --platform managed --allow-unauthenticated --service-account="firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com" --set-env-vars=VECTOR_SEARCH_ENDPOINT_ID=projects/922976482476/locations/asia-south1/indexEndpoints/2041203754547544064,VECTOR_SEARCH_INDEX_ID=6474496210391531520,DEPLOYED_INDEX_ID=serena_memory_deployedv2,GOOGLE_CLOUD_PROJECT=genai-bot-kdf,REGION=asia-south1,KMS_LOCATION=asia-south1,KMS_KEYRING=chatbot-encryption,KMS_KEY=memory-encryption-key
    ```
    **Note:** The `--set-env-vars` flag *replaces* all existing variables. Ensure you always provide the full, correct list.

### ### How to Update the Frontend
To make changes to your React application (e.g., change some text or styling).

1.  **Make your code changes** in the `genai-frontend/src` directory and save them.
2.  Navigate to the `genai-frontend/` directory:
    ```bash
    cd genAI/genai-frontend
    ```
3.  Run the **build** and **deploy** commands:
    ```bash
    # Step 1: Re-build the React app with your changes
    npm run build

    # Step 2: Deploy the new version to Firebase Hosting
    firebase deploy --only hosting
    ```
4.  **Important:** After deploying frontend changes, you may need to do a hard refresh (**Ctrl+Shift+R** or **Cmd+Shift+R**) in your browser to see the updates.

---

## 5. Required Environment Variables (Cloud Run)

The backend service **requires** the following environment variables to be set during deployment:

-   `GOOGLE_CLOUD_PROJECT`: Your GCP Project ID (e.g., `genai-bot-kdf`).
-   `REGION`: The region where your services are deployed (e.g., `asia-south1`).
-   `VECTOR_SEARCH_ENDPOINT_ID`: The **numerical ID** of your deployed Vector Search Endpoint.
-   `DEPLOYED_INDEX_ID`: The **string ID** you gave your deployed index on the endpoint.
-   `KMS_LOCATION`: The region of your KMS KeyRing (e.g., `asia-south1`).
-   `KMS_KEYRING`: The name of your KMS KeyRing (e.g., `chatbot-encryption`).
-   `KMS_KEY`: The name of your KMS Key (e.g., `memory-encryption-key`).

---

## 6. Security Best Practices

-   **Service Account Key:** The `service-account-key.json` file is only for local development/testing and should **NEVER** be committed to Git. Cloud Run uses the attached service account.
-   **API Security:** Ensure sensitive endpoints like `/delete_memories` use the user ID from the verified authentication token (`request.user_id`) and not from the client payload.
-   **KMS Permissions:** Ensure only the necessary service account has the `Cloud KMS CryptoKey Encrypter/Decrypter` role.
-   **CORS Policy:** For better security in production, consider changing the CORS origin in `main.py` from `"*"` to your specific Firebase Hosting URL: `https://genai-bot-kdf.web.app`.