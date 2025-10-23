# GenAI Chatbot - Production & Deployment Guide

This document provides all the necessary steps to deploy and maintain the GenAI Chatbot application. The application consists of a Python (Flask) backend running on **Google Cloud Run** and a React frontend hosted on **Firebase Hosting**.

## 1. Prerequisites
Before deploying, ensure you have the following tools installed and configured:

- **Git:** For cloning the repository.
- **Google Cloud CLI (`gcloud`):** [Installation Guide](https://cloud.google.com/sdk/docs/install)
- **Firebase Tools (`firebase`):** Install via npm: `npm install -g firebase-tools`
- **Node.js (LTS):** For managing the frontend application.

---
## 2. Initial Deployment (From a Fresh Start)
Follow these steps to deploy the entire application from scratch.

### ### Phase A: Local Setup
1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/Dev-solder124/genAI.git](https://github.com/Dev-solder124/genAI.git)
    cd genAI
    ```
2.  **Add Service Account Key:**
    Download your `service-account-key.json` file from your Google Cloud project's IAM & Admin page. Place this file in the root `genAI/` directory. **This file must not be committed to Git.**

3.  **Configure Cloud Tools:**
    Log in and select your project.
    ```bash
    gcloud init
    firebase login
    ```
### ### Phase B: Deploy the Backend
All commands should be run from the root `genAI/` directory.

1.  **Build the Container Image:**
    This command packages your Python application into a Docker container using Google Cloud Build.
    ```bash
    gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot
    ```
2.  **Deploy to Cloud Run:**
    This command launches the container as a live, scalable service.
    ```bash
    gcloud run deploy genai-chatbot --image gcr.io/genai-bot-kdf/genai-chatbot --region=asia-south1 --allow-unauthenticated --platform managed --service-account="firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com"
    ```
    After this step, you will receive a **Service URL** (e.g., `https://genai-chatbot-....run.app`). **Copy this URL.**

### ### Phase C: Deploy the Frontend
1.  **Navigate to the Frontend Directory:**
    ```bash
    cd genai-frontend
    ```
2.  **Create Production Environment File:**
    Create a new file named `.env.production`. Paste the following content, adding your live backend URL and your public Firebase keys.
    ```
    # Backend URL from the previous step
    VITE_API_BASE_URL=[https://genai-chatbot-....run.app](https://genai-chatbot-....run.app)

    # Your public Firebase keys
    VITE_FIREBASE_API_KEY=AIzaSy...
    VITE_FIREBASE_AUTH_DOMAIN=genai-bot-kdf.firebaseapp.com
    VITE_FIREBASE_PROJECT_ID=genai-bot-kdf
    VITE_FIREBASE_STORAGE_BUCKET=genai-bot-kdf.appspot.com
    VITE_FIREBASE_MESSAGING_SENDER_ID=9...
    VITE_FIREBASE_APP_ID=1:9...
    ```
3.  **Install Dependencies:**
    ```bash
    npm install
    ```
4.  **Initialize Firebase Hosting:**
    ```bash
    firebase init hosting
    ```
    - Select **Use an existing project** (`genai-bot-kdf`).
    - For the public directory, enter **`dist`**.
    - Configure as a single-page app: **`Yes`**.
    - Set up automatic builds with GitHub: **`No`**.

5.  **Build and Deploy:**
    ```bash
    npm run build
    firebase deploy
    ```
    After this step, you will receive a **Hosting URL** (e.g., `https://genai-bot-kdf.web.app`). This is your live application.

---
## 3. How to Update the Application
Once deployed, you don't need to repeat the whole process. Follow these simpler steps to update.

### ### How to Update the Backend
To make changes to your Python code (e.g., update a prompt in `main.py`).

1.  **Make your code changes** and save the files.
2.  From the root `genAI/` directory, run the **build** and **deploy** commands again:
    ```bash
    # Step 1: Re-build the container with your changes
    gcloud builds submit --tag gcr.io/genai-bot-kdf/genai-chatbot

    # Step 2: Re-deploy the new container version
    gcloud run deploy genai-chatbot --image gcr.io/genai-bot-kdf/genai-chatbot --region=asia-south1 --allow-unauthenticated --platform managed --service-account="firebase-adminsdk-fbsvc@genai-bot-kdf.iam.gserviceaccount.com"
    ```
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
    firebase deploy
    ```
4.  **Important:** After deploying frontend changes, you may need to do a hard refresh (**Ctrl+Shift+R** or **Cmd+Shift+R**) in your browser to see the updates.

---
## 4. Security Best Practices
- **Service Account Key:** The `service-account-key.json` file should **NEVER** be committed to a public Git repository.
- **API Security:** Ensure sensitive endpoints like `/delete_memories` use the user ID from the verified authentication token (`request.user_id`) and not from the client payload.
- **CORS Policy:** For better security, consider changing the CORS origin in `main.py` from `"*"` to your specific Firebase Hosting URL: `https://genai-bot-kdf.web.app`.