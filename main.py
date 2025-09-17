# main.py
import os
import json
import numpy as np
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import aiplatform
from datetime import datetime, timezone

# CONFIG: set these BEFORE running or rely on env vars
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT") or "genai-bot-kdf"
REGION = os.environ.get("REGION", "asia-south1")

# model names: confirm these in Vertex AI or replace with model available in your region
LLM_MODEL = os.environ.get("LLM_MODEL", "text-bison@001")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "textembedding-gecko@001")

# init Vertex AI (uses Application Default Credentials)
aiplatform.init(project=PROJECT_ID, location=REGION)
db = firestore.Client(project=PROJECT_ID)

app = Flask(__name__)

# --- simple cosine
def cosine_similarity(a: np.ndarray, b: np.ndarray):
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# --- embeddings wrapper
def embed_texts(texts):
    client = aiplatform.gapic.EmbeddingsClient(client_options={"api_endpoint": f"{REGION}-aiplatform.googleapis.com"})
    response = client.embed(model=EMBEDDING_MODEL, input=texts)
    vectors = [np.array(e.values) for e in response.embeddings]
    return vectors

# --- text generation wrapper
def generate_text(prompt, max_output_tokens=300, temperature=0.2):
    pred_client = aiplatform.gapic.PredictionServiceClient(client_options={"api_endpoint": f"{REGION}-aiplatform.googleapis.com"})
    instance = {"content": prompt}
    endpoint = f"projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{LLM_MODEL}"
    response = pred_client.predict(endpoint=endpoint, instances=[instance], parameters={"temperature": temperature, "maxOutputTokens": max_output_tokens})
    if response.predictions and len(response.predictions) > 0:
        pred = response.predictions[0]
        if isinstance(pred, dict):
            return pred.get("content") or pred.get("output") or json.dumps(pred)
        return str(pred)
    return ""

# --- Firestore helpers
def get_user_profile(user_id):
    doc = db.collection("users").document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def upsert_user_profile(user_id, profile):
    db.collection("users").document(user_id).set(profile, merge=True)

def save_memory(user_id, summary_text, metadata=None):
    if metadata is None:
        metadata = {}
    created_at = datetime.now(timezone.utc).isoformat()
    vec = embed_texts([summary_text])[0].tolist()
    mem_doc = {
        "user_id": user_id,
        "summary": summary_text,
        "embedding": vec,
        "metadata": metadata,
        "created_at": created_at
    }
    db.collection("memories").add(mem_doc)
    return True

def retrieve_similar_memories(user_id, query_text, top_k=3):
    q_vec = embed_texts([query_text])[0]
    docs = db.collection("memories").where("user_id", "==", user_id).stream()
    scored = []
    for d in docs:
        data = d.to_dict()
        emb = np.array(data.get("embedding", []))
        if emb.size == 0:
            continue
        score = cosine_similarity(q_vec, emb)
        scored.append((score, data))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]

def summarize_conversation(turns_text):
    prompt = "Summarize the following conversation in 2-3 sentences and list any coping strategies or preferences mentioned:\n\n" + turns_text + "\n\nSummary:"
    return generate_text(prompt, max_output_tokens=200, temperature=0.2)

# --- session buffer stored in Firestore
def append_session_turn(user_id, user_text, assistant_text):
    ref = db.collection("session_buffers").document(user_id)
    doc = ref.get()
    turns = doc.to_dict().get("turns", []) if doc.exists else []
    turns.append({"user": user_text, "assistant": assistant_text, "ts": datetime.now(timezone.utc).isoformat()})
    if len(turns) > 60:
        turns = turns[-60:]
    ref.set({"turns": turns, "updated_at": datetime.now(timezone.utc).isoformat()})
    return turns

# --- Dialogflow webhook endpoint
@app.route("/dialogflow-webhook", methods=["POST"])
def dialogflow_webhook():
    req = request.get_json(silent=True) or {}
    session = req.get("session", "")
    session_id = session.split("/")[-1] if session else "unknown_session"
    user_id = req.get("sessionInfo", {}).get("parameters", {}).get("user_id") or session_id

    # parse user message
    user_text = ""
    for m in req.get("messages", []):
        if m.get("text"):
            user_text = m["text"].get("text", [""])[0]
            break
    if not user_text:
        user_text = req.get("text", "") or "Hello"

    user_profile = get_user_profile(user_id) or {"user_id": user_id, "consent": False}

    # if no consent, ask for consent
    if not user_profile.get("consent", False):
        reply_text = "I can remember helpful things between sessions to better support you. Would you like me to remember parts of this conversation for next time? (yes/no)"
        return jsonify({"fulfillment_response": {"messages":[{"text": {"text":[reply_text]}}]}})

    # retrieve relevant memories
    retrieved = retrieve_similar_memories(user_id, user_text, top_k=3)
    retrieved_text = "\n".join([f"- {r.get('summary')} (tags={r.get('metadata', {}).get('topic')})" for r in retrieved]) if retrieved else ""

    session_params = req.get("sessionInfo", {}).get("parameters", {})
    short_term = json.dumps(session_params) if session_params else ""

    prompt = (
        "You are EmpathicBot — supportive, validating, non-judgemental. If crisis language, provide crisis resources.\n\n"
        f"User profile: {json.dumps(user_profile)}\n"
        f"Retrieved memories:\n{retrieved_text}\n\n"
        f"Session params: {short_term}\n\n"
        f"User: {user_text}\n\n"
        "Assistant (empathetic, concise, reference past coping strategies):"
    )

    reply_text = generate_text(prompt, max_output_tokens=250, temperature=0.7).strip()
    print("Reply text:", reply_text)

    turns = append_session_turn(user_id, user_text, reply_text)
    if len(turns) >= 8:
        combined_text = "\n".join([f"User: {t['user']}\nAssistant: {t['assistant']}" for t in turns])
        summary = summarize_conversation(combined_text)
        save_memory(user_id, summary, {"topic":"session_summary"})
        # keep only last 2 turns after summarizing
        db.collection("session_buffers").document(user_id).set({"turns": turns[-2:], "updated_at": datetime.now(timezone.utc).isoformat()})

    return jsonify({"fulfillment_response": {"messages":[{"text": {"text":[reply_text]}}]}})

# --- consent endpoint
@app.route("/consent", methods=["POST"])
def consent():
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    consent_flag = bool(payload.get("consent", False))
    if not user_id:
        return jsonify({"error":"user_id required"}), 400
    upsert_user_profile(user_id, {"consent": consent_flag, "updated_at": datetime.now(timezone.utc).isoformat()})
    return jsonify({"ok": True, "user_id": user_id, "consent": consent_flag})

# --- delete memories
@app.route("/delete_memories", methods=["POST"])
def delete_memories():
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error":"user_id required"}), 400
    mems = db.collection("memories").where("user_id","==",user_id).stream()
    count = 0
    for m in mems:
        m.reference.delete()
        count += 1
    return jsonify({"ok": True, "deleted": count})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    
