import os
import json
import logging
import traceback
import numpy as np
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import aiplatform
from datetime import datetime, timezone
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CONFIG: Updated model configuration for Gemini
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT") or "genai-bot-kdf"
REGION = os.environ.get("REGION", "asia-south1")

# Updated to use Gemini models (Bison models are deprecated)
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")

logger.info(f"Starting chatbot with config:")
logger.info(f"   PROJECT_ID: {PROJECT_ID}")
logger.info(f"   REGION: {REGION}")
logger.info(f"   LLM_MODEL: {LLM_MODEL}")
logger.info(f"   EMBEDDING_MODEL: {EMBEDDING_MODEL}")

# init Vertex AI (uses Application Default Credentials)
try:
    aiplatform.init(project=PROJECT_ID, location=REGION)
    logger.info("Vertex AI initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI: {e}")
    logger.error(traceback.format_exc())

try:
    db = firestore.Client(project=PROJECT_ID)
    logger.info("Firestore client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    logger.error(traceback.format_exc())

app = Flask(__name__)

# Function to list available models for debugging
def list_available_models():
    try:
        from google.cloud import aiplatform
        client = aiplatform.gapic.ModelServiceClient(
            client_options={"api_endpoint": f"{REGION}-aiplatform.googleapis.com"}
        )
        parent = f"projects/{PROJECT_ID}/locations/{REGION}"
        
        logger.info(f"Listing models in {parent}")
        models = client.list_models(parent=parent)
        
        available_models = []
        for model in models:
            available_models.append({
                "name": model.name,
                "display_name": model.display_name
            })
            logger.info(f"Available model: {model.display_name} - {model.name}")
        
        return available_models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []

# Add a health check endpoint with improved model testing
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify all services are working"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    
    # Test Firestore
    try:
        test_ref = db.collection("health_check").document("test")
        test_ref.set({"test": True, "timestamp": datetime.now(timezone.utc).isoformat()})
        test_ref.delete()
        health_status["services"]["firestore"] = "OK"
        logger.info("Firestore health check passed")
    except Exception as e:
        health_status["services"]["firestore"] = f"ERROR: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error(f"Firestore health check failed: {e}")
    
    # Test Vertex AI Embedding
    try:
        test_embedding = embed_texts(["health check test"])
        if test_embedding and len(test_embedding) > 0:
            health_status["services"]["vertex_ai_embeddings"] = "OK"
            logger.info("Vertex AI embeddings health check passed")
        else:
            health_status["services"]["vertex_ai_embeddings"] = "ERROR: No embeddings returned"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["services"]["vertex_ai_embeddings"] = f"ERROR: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error(f"Vertex AI embeddings health check failed: {e}")
    
    # Test Vertex AI Text Generation with multiple models
    try:
        
        test_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
        success = False
        working_model = None
        
        for model in test_models:
            try:
                logger.debug(f"Testing model: {model}")
                test_response = generate_text_with_model(
                    "Say 'hello' if you can hear me", 
                    model_name=model,
                    max_output_tokens=10
                )
                if test_response and test_response.strip() and "trouble" not in test_response.lower():
                    health_status["services"]["vertex_ai_generation"] = f"OK (using {model})"
                    logger.info(f"Vertex AI generation health check passed with {model}")
                    working_model = model
                    success = True
                    break
            except Exception as model_error:
                logger.debug(f"Model {model} failed in health check: {model_error}")
                continue
        
        if not success:
            health_status["services"]["vertex_ai_generation"] = "ERROR: All models failed"
            health_status["status"] = "unhealthy"
        else:
            # Update global model to working one
            global LLM_MODEL
            LLM_MODEL = working_model
            
    except Exception as e:
        health_status["services"]["vertex_ai_generation"] = f"ERROR: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error(f"Vertex AI text generation health check failed: {e}")
    
    return jsonify(health_status), 200 if health_status["status"] == "healthy" else 503

# --- simple cosine with debugging
def cosine_similarity(a: np.ndarray, b: np.ndarray):
    try:
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            logger.debug("Cosine similarity: One vector has zero norm")
            return 0.0
        similarity = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        logger.debug(f"Cosine similarity calculated: {similarity:.4f}")
        return similarity
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0

# --- embeddings wrapper with debugging
def embed_texts(texts):
    try:
        logger.debug(f"Embedding {len(texts)} texts")
        logger.debug(f"Texts preview: {[t[:50] + '...' if len(t) > 50 else t for t in texts]}")
        
        from vertexai.language_models import TextEmbeddingModel
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings(texts)
        vectors = [np.array(embedding.values) for embedding in embeddings]
        
        logger.debug(f"Successfully generated {len(vectors)} embeddings")
        logger.debug(f"Embedding dimensions: {[len(v) for v in vectors]}")
        return vectors
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        logger.error(traceback.format_exc())
        raise

# --- Updated text generation with Gemini model support
# --- Updated text generation with the modern Generative AI SDK
def generate_text_with_model(prompt, model_name=None, max_output_tokens=300, temperature=0.2):
    try:
        if model_name is None:
            model_name = LLM_MODEL

        logger.debug(f"Generating text with model: {model_name} using the GenerativeModel SDK")
        logger.debug(f"Prompt preview: {prompt[:200]}...")

        # Initialize the model from the high-level SDK
        model = GenerativeModel(model_name)
        
        # Configure generation parameters
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=max_output_tokens
        )
        
        # Generate content
        response = model.generate_content(
            contents=[prompt],
            generation_config=generation_config
        )
        
        logger.debug(f"Raw response from {model_name}: {response}")
        
        # Extract the text from the response
        result = response.text
        logger.debug(f"Generated text: {result[:100]}...")
        return result

    except Exception as e:
        logger.error(f"Error generating text with {model_name}: {e}")
        logger.error(traceback.format_exc())
        raise

def generate_text(prompt, max_output_tokens=300, temperature=0.2):
    """Main text generation function with fallback models"""
    fallback_models = [
        LLM_MODEL,
        "gemini-1.5-pro", # A good alternative
        "gemini-1.0-pro",
        "gemini-pro"
    ]
    
    # Remove duplicates while preserving order
    models_to_try = []
    for model in fallback_models:
        if model not in models_to_try:
            models_to_try.append(model)
    
    for model_name in models_to_try:
        try:
            result = generate_text_with_model(
                prompt, 
                model_name=model_name,
                max_output_tokens=max_output_tokens,
                temperature=temperature
            )
            if result and result.strip():
                return result
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue
    
    logger.error("All models failed to generate text")
    return "I'm having trouble generating a response right now. Please try again in a moment."

# --- Firestore helpers with debugging
def get_user_profile(user_id):
    try:
        logger.debug(f"Getting user profile for: {user_id}")
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            profile = doc.to_dict()
            logger.debug(f"Found user profile: {profile}")
            return profile
        else:
            logger.debug(f"No profile found for user: {user_id}")
            return None
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        logger.error(traceback.format_exc())
        return None

def upsert_user_profile(user_id, profile):
    try:
        logger.debug(f"Upserting profile for {user_id}: {profile}")
        db.collection("users").document(user_id).set(profile, merge=True)
        logger.debug(f"Profile upserted successfully for {user_id}")
    except Exception as e:
        logger.error(f"Error upserting user profile: {e}")
        logger.error(traceback.format_exc())
        raise

def save_memory(user_id, summary_text, metadata=None):
    try:
        if metadata is None:
            metadata = {}
        
        logger.debug(f"Saving memory for {user_id}")
        logger.debug(f"Summary: {summary_text[:100]}...")
        logger.debug(f"Metadata: {metadata}")
        
        created_at = datetime.now(timezone.utc).isoformat()
        vec = embed_texts([summary_text])[0].tolist()
        
        mem_doc = {
            "user_id": user_id,
            "summary": summary_text,
            "embedding": vec,
            "metadata": metadata,
            "created_at": created_at
        }
        
        doc_ref = db.collection("memories").add(mem_doc)
        logger.debug(f"Memory saved with ID: {doc_ref[1].id}")
        return True
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        logger.error(traceback.format_exc())
        return False

def retrieve_similar_memories(user_id, query_text, top_k=3):
    try:
        logger.debug(f"Retrieving similar memories for {user_id}")
        logger.debug(f"Query: {query_text[:100]}...")
        
        q_vec = embed_texts([query_text])[0]
        docs = db.collection("memories").where("user_id", "==", user_id).stream()
        
        scored = []
        doc_count = 0
        for d in docs:
            doc_count += 1
            data = d.to_dict()
            emb = np.array(data.get("embedding", []))
            if emb.size == 0:
                logger.debug(f"Empty embedding in document {d.id}")
                continue
            score = cosine_similarity(q_vec, emb)
            scored.append((score, data))
            logger.debug(f"Doc {d.id}: similarity = {score:.4f}")
        
        logger.debug(f"Found {doc_count} total memories, {len(scored)} with valid embeddings")
        
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored[:top_k]]
        
        logger.debug(f"Returning top {len(results)} similar memories")
        for i, result in enumerate(results):
            logger.debug(f"   #{i+1}: {result.get('summary', '')[:50]}...")
        
        return results
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        logger.error(traceback.format_exc())
        return []

def summarize_conversation(turns_text):
    try:
        logger.debug(f"Summarizing conversation ({len(turns_text)} chars)")
        prompt = (
            "Carefully analyze the following conversation. Your task is to create a concise summary focusing on the user's emotional state, key topics, and any coping strategies discussed.\n"
            "**Specifically list any successful strategies the user mentioned from their past (e.g., tutoring, specific hobbies, etc.).**\n\n"
            f"Conversation:\n{turns_text}\n\n"
            "Summary:"
        )
        
        # This is the missing line that calls the AI
        summary = generate_text(prompt, max_output_tokens=200, temperature=0.2)
        
        logger.debug(f"Generated summary: {summary[:100]}...")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing conversation: {e}")
        logger.error(traceback.format_exc())
        return "Error generating summary"
    
# --- session buffer stored in Firestore with debugging
def append_session_turn(user_id, user_text, assistant_text):
    try:
        logger.debug(f"Appending session turn for {user_id}")
        logger.debug(f"User: {user_text[:50]}...")
        logger.debug(f"Assistant: {assistant_text[:50]}...")
        
        ref = db.collection("session_buffers").document(user_id)
        doc = ref.get()
        turns = doc.to_dict().get("turns", []) if doc.exists else []
        
        logger.debug(f"Current buffer has {len(turns)} turns")
        
        turns.append({
            "user": user_text, 
            "assistant": assistant_text, 
            "ts": datetime.now(timezone.utc).isoformat()
        })
        
        if len(turns) > 60:
            logger.debug("Trimming buffer to last 60 turns")
            turns = turns[-60:]
        
        ref.set({
            "turns": turns, 
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        logger.debug(f"Session buffer updated, now has {len(turns)} turns")
        return turns
    except Exception as e:
        logger.error(f"Error appending session turn: {e}")
        logger.error(traceback.format_exc())
        return []

# --- Dialogflow webhook endpoint with enhanced debugging
@app.route("/dialogflow-webhook", methods=["POST"])
def dialogflow_webhook():
    try:
        logger.info("=== NEW WEBHOOK REQUEST ===")
        req = request.get_json(silent=True) or {}
        logger.debug(f"Raw request: {json.dumps(req, indent=2)}")
        
        session = req.get("session", "")
        session_id = session.split("/")[-1] if session else "unknown_session"
        user_id = req.get("sessionInfo", {}).get("parameters", {}).get("user_id") or session_id
        
        logger.info(f"Processing request for user_id: {user_id}")
        logger.info(f"Session: {session_id}")

        # parse user message
        user_text = ""
        for m in req.get("messages", []):
            if m.get("text"):
                user_text = m["text"].get("text", [""])[0]
                break
        if not user_text:
            user_text = req.get("text", "") or "Hello"

        logger.info(f"User message: '{user_text}'")

        user_profile = get_user_profile(user_id) or {"user_id": user_id, "consent": False}
        logger.info(f"User consent status: {user_profile.get('consent', False)}")

        # if no consent, ask for consent
        if not user_profile.get("consent", False):
            reply_text = "I can remember helpful things between sessions to better support you. Would you like me to remember parts of this conversation for next time? (yes/no)"
            logger.info(f"Sending consent request")
            return jsonify({"fulfillment_response": {"messages":[{"text": {"text":[reply_text]}}]}})

        # retrieve relevant memories
        logger.info("Retrieving similar memories...")
        retrieved = retrieve_similar_memories(user_id, user_text, top_k=3)
        retrieved_text = "\n".join([f"- {r.get('summary')} (tags={r.get('metadata', {}).get('topic')})" for r in retrieved]) if retrieved else ""
        logger.info(f"Found {len(retrieved)} relevant memories")

        session_params = req.get("sessionInfo", {}).get("parameters", {})
        short_term = json.dumps(session_params) if session_params else ""
        logger.debug(f"Session params: {short_term}")

        prompt = (
            "You are EmpathicBot — a supportive, validating, and non-judgemental AI assistant. Your primary goal is to listen and help the user feel heard. Crucially, if you are provided with retrieved memories, seamlessly weave the specific details from them into your response to show you remember the user's context.For example, if a memory mentions the user found 'tutoring' helpful, you should reference 'tutoring' directly. Do not use generic placeholders like '[mention coping strategy]' Always be concise and empathetic."
            f"Retrieved memories:\n{retrieved_text}\n\n"
            f"User profile: {json.dumps(user_profile)}\n"
            f"Session params: {short_term}\n\n"
            f"User: {user_text}\n\n"
            "Assistant (empathetic, concise, reference past coping strategies):"
        )

        logger.info("Generating response...")
        reply_text = generate_text(prompt, max_output_tokens=250, temperature=0.7).strip()
        logger.info(f"Generated reply: '{reply_text}'")

        logger.info("Updating session buffer...")
        turns = append_session_turn(user_id, user_text, reply_text)
        
        # Check if we need to summarize
        if len(turns) >= 8:
            logger.info("Buffer threshold reached, creating summary...")
            combined_text = "\n".join([f"User: {t['user']}\nAssistant: {t['assistant']}" for t in turns])
            summary = summarize_conversation(combined_text)
            
            if save_memory(user_id, summary, {"topic":"session_summary"}):
                logger.info("Memory saved, trimming buffer...")
                # keep only last 2 turns after summarizing
                db.collection("session_buffers").document(user_id).set({
                    "turns": turns[-2:], 
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.error("Failed to save memory")

        response = {"fulfillment_response": {"messages":[{"text": {"text":[reply_text]}}]}}
        logger.info("Request completed successfully")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in dialogflow_webhook: {e}")
        logger.error(traceback.format_exc())
        error_response = {"fulfillment_response": {"messages":[{"text": {"text":["I'm having trouble right now. Please try again in a moment."]}}]}}
        return jsonify(error_response), 500

# --- consent endpoint with debugging
@app.route("/consent", methods=["POST"])
def consent():
    try:
        logger.info("=== CONSENT REQUEST ===")
        payload = request.get_json(silent=True) or {}
        logger.debug(f"Consent payload: {payload}")
        
        user_id = payload.get("user_id")
        consent_flag = bool(payload.get("consent", False))
        
        if not user_id:
            logger.warning("Missing user_id in consent request")
            return jsonify({"error":"user_id required"}), 400
        
        logger.info(f"Setting consent for {user_id}: {consent_flag}")
        upsert_user_profile(user_id, {
            "consent": consent_flag, 
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info("Consent updated successfully")
        return jsonify({"ok": True, "user_id": user_id, "consent": consent_flag})
    
    except Exception as e:
        logger.error(f"Error in consent endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# --- delete memories with debugging
@app.route("/delete_memories", methods=["POST"])
def delete_memories():
    try:
        logger.info("=== DELETE MEMORIES REQUEST ===")
        payload = request.get_json(silent=True) or {}
        logger.debug(f"Delete payload: {payload}")
        
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Missing user_id in delete request")
            return jsonify({"error":"user_id required"}), 400
        
        logger.info(f"Deleting memories for user: {user_id}")
        mems = db.collection("memories").where("user_id","==",user_id).stream()
        
        count = 0
        for m in mems:
            m.reference.delete()
            count += 1
            logger.debug(f"Deleted memory {m.id}")
        
        logger.info(f"Deleted {count} memories for {user_id}")
        return jsonify({"ok": True, "deleted": count})
    
    except Exception as e:
        logger.error(f"Error in delete_memories endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# --- Debug endpoint to list available models
@app.route("/debug/models", methods=["GET"])
def debug_models():
    try:
        logger.info("=== DEBUG MODELS REQUEST ===")
        models = list_available_models()
        return jsonify({
            "available_models": models,
            "current_config": {
                "project_id": PROJECT_ID,
                "region": REGION,
                "llm_model": LLM_MODEL,
                "embedding_model": EMBEDDING_MODEL
            }
        })
    except Exception as e:
        logger.error(f"Error in debug_models endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))