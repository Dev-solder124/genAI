import os
import json
import logging
import traceback
import numpy as np
import re
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

# Function to sanitize user_id for use as Firestore collection name
def sanitize_collection_name(user_id):
    """Sanitize user_id to be valid Firestore collection name"""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"user_{sanitized}"
    # Ensure minimum length
    if not sanitized:
        sanitized = "anonymous_user"
    logger.debug(f"Sanitized user_id '{user_id}' to '{sanitized}'")
    return sanitized

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
        test_collection = sanitize_collection_name("health_check_user")
        test_ref = db.collection(test_collection).document("profile").collection("test").document("health")
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
        
        test_models = ["gemini-1.5-flash"]
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
        "gemini-1.5-flash",
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

# --- Updated Firestore helpers for new structure
def get_user_profile(user_id):
    try:
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Getting user profile for: {user_id} (sanitized: {sanitized_user_id})")
        
        
        doc_ref = db.collection("users").document(sanitized_user_id)
        doc = doc_ref.get()

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
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Upserting profile for {user_id}: {profile}")

        # CORRECTED LOGIC: Create a nested dictionary for the 'profile' map
        # This is the correct format for .set() with merge=True
        update_data = {
            "profile": profile
        }
        
        db.collection("users").document(sanitized_user_id).set(update_data, merge=True)
        
        logger.debug(f"Profile upserted successfully for {user_id}")

    except Exception as e:
        logger.error(f"Error upserting user profile: {e}")
        logger.error(traceback.format_exc())
        raise

def save_memory(user_id, summary_text, metadata=None):
    try:
        if metadata is None:
            metadata = {}
        
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Saving memory for {user_id} (sanitized: {sanitized_user_id})")
        logger.debug(f"Summary: {summary_text[:100]}...")
        logger.debug(f"Metadata: {metadata}")
        
        created_at = datetime.now(timezone.utc).isoformat()
        vec = embed_texts([summary_text])[0].tolist()
        
        # Use timestamp-based ID for memory documents
        memory_id = f"mem_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        mem_doc = {
            "user_id": user_id,
            "summary": summary_text,
            "embedding": vec,
            "metadata": metadata,
            "created_at": created_at
        }
        
        db.collection("users").document(sanitized_user_id).collection("memories").document(memory_id).set(mem_doc)

        logger.debug(f"Memory saved with ID: {memory_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        logger.error(traceback.format_exc())
        return False

def retrieve_similar_memories(user_id, query_text, top_k=3):
    try:
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Retrieving similar memories for {user_id} (sanitized: {sanitized_user_id})")
        logger.debug(f"Query: {query_text[:100]}...")
        
        q_vec = embed_texts([query_text])[0]
        
        
        docs = db.collection("users").document(sanitized_user_id).collection("memories").stream()
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

def summarize_conversation(user_text, assistant_text):
    try:
        logger.debug("Summarizing and evaluating the latest exchange.")
        exchange_text = f"User: {user_text}\nAssistant: {assistant_text}"

        prompt = (
            "You are a data analysis AI. Your task is to analyze a user-assistant exchange and determine if it contains significant information worth saving as a long-term memory. After your decision, you will provide a factual summary.\n\n"
            "**Instructions:**\n"
            "1.  **Significance Decision:** On the first line, write 'SIGNIFICANT: YES' if the user **introduces a new important topic, person, or entity (like a name or place)**, expresses a strong emotion for the first time, or reveals a specific goal. Write 'SIGNIFICANT: NO' only for simple greetings, affirmations ('ok', 'yes').\n"
            "2.  **Summary:** On the next line, write 'SUMMARY:' followed by a concise, factual, third-person summary. **You must preserve specific names and entities.**\n\n"
            f"**Exchange to Analyze:**\n{exchange_text}\n\n"
            "**Your Analysis:**"
        )
        
        # We ask for a slightly longer response to accommodate the structured output
        analysis_text = generate_text(prompt, max_output_tokens=200, temperature=0.1)
        
        # --- NEW PARSING LOGIC ---
        lines = analysis_text.strip().split('\n')
        is_significant = False
        summary = "No summary generated."

        # Robustly parse the output
        if lines:
            if "yes" in lines[0].lower():
                is_significant = True
            
            # Find the summary line
            summary_line = next((line for line in lines if "summary:" in line.lower()), None)
            if summary_line:
                summary = summary_line.split(":", 1)[1].strip()

        logger.debug(f"Significance: {is_significant}, Summary: {summary[:100]}...")
        
        return {
            "is_significant": is_significant,
            "summary": summary
        }
            
    except Exception as e:
        logger.error(f"Error summarizing exchange: {e}")
        logger.error(traceback.format_exc())
        return {
            "is_significant": False,
            "summary": "Error generating summary"
        }
 

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

        user_profile = get_user_profile(user_id) or {}
        
        # CORRECTED LINE: Access the consent flag inside the 'profile' map
        has_consent = user_profile.get("profile", {}).get("consent", False)
        
        logger.info(f"User consent status: {has_consent}")

        # if no consent, ask for consent
        if not has_consent:
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
            "You are an Empathetic bot, here to help users cope with the mental health issues they tell you about. Your role is to provide support and validate their situation. Be culturally sensitive, inclusive, empathetic, and maintain a friendly, warm tone. Your goal is to actively listen and reciprocate, gathering a 360-degree understanding of their situation before suggesting any solutions. Be very cautious with your responses, as this is a sensitive topic. Always prioritize transparency and confidentiality to maintain the user's trust."
            
            "\n\nIf you are given retrieved memories, analyze them to understand the user's usual behavior, preferences, and dislikes. Seamlessly weave the specific details from these memories into your response to validate the user and show you remember their context."

            "\n\nMost importantly, if a user is at risk of self-harm, you must prioritize providing appropriate emergency resources and contact information."

            f"\n\n--- CONTEXT ---"
            f"\nRetrieved memories:\n{retrieved_text}\n"
            f"\nUser profile: {json.dumps(user_profile)}\n"
            f"\nSession params: {short_term}\n"
            f"\n--- END CONTEXT ---"

            f"\n\nUser: {user_text}\n\n"

            "Assistant:"
        )

        logger.info("Generating response...")
        reply_text = generate_text(prompt, max_output_tokens=250, temperature=0.7).strip()
        logger.info(f"Generated reply: '{reply_text}'")

        # --- UPDATED LOGIC: Summarize, evaluate, and save if significant ---
        logger.info("Creating and evaluating summary of the current exchange...")
        analysis_result = summarize_conversation(user_text, reply_text)
        
        # Only save the memory if the analysis flagged it as significant
        if analysis_result.get("is_significant"):
            summary = analysis_result.get("summary")
            if "error" not in summary.lower():
                if save_memory(user_id, summary, {"topic": "conversation_exchange", "session_id": session_id}):
                    logger.info("SIGNIFICANT exchange saved as a new memory.")
                else:
                    logger.error("Failed to save significant exchange as memory.")
            else:
                logger.warning("Skipping memory save due to summary generation error.")
        else:
            logger.info("Exchange was not significant. Skipping memory save.")

        response = {"fulfillment_response": {"messages":[{"text": {"text":[reply_text]}}]}}
        logger.info("Request completed successfully")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in dialogflow_webhook: {e}")
        logger.error(traceback.format_exc())
        error_response = {"fulfillment_response": {"messages":[{"text": {"text":["I'm having trouble right now. Please try again in a moment."]}}]}}
        return jsonify(error_response), 500

# --- consent endpoint with debugging
# In main.py
@app.route("/consent", methods=["POST"])
def consent():
    try:
        logger.info("=== CONSENT/PROFILE UPDATE REQUEST ===")
        payload = request.get_json(silent=True) or {}
        logger.debug(f"Payload: {payload}")
        
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Missing user_id in request")
            return jsonify({"error":"user_id required"}), 400

        # Prepare a dictionary to hold all profile data from the request
        profile_data = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Check for and add 'consent' if it exists in the payload
        if 'consent' in payload:
            profile_data['consent'] = bool(payload['consent'])
            logger.info(f"Updating consent for {user_id}: {profile_data['consent']}")

        # Check for and add 'username' if it exists in the payload
        if 'username' in payload:
            profile_data['username'] = payload['username']
            logger.info(f"Updating username for {user_id}: {profile_data['username']}")

        # Upsert the collected profile data
        upsert_user_profile(user_id, profile_data)
        
        logger.info(f"Profile for {user_id} updated successfully.")
        return jsonify({"ok": True, "user_id": user_id, "data_updated": profile_data})
    
    except Exception as e:
        logger.error(f"Error in consent/profile endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
# --- delete memories with debugging for new structure
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
        
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.info(f"Deleting memories for user: {user_id} (sanitized: {sanitized_user_id})")
        
        # Delete all memories in the user's memory subcollection
        mems = db.collection("users").document(sanitized_user_id).collection("memories").stream()
        
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