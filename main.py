import os
import json
import logging
import traceback
import numpy as np
import re
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, ValidationError
from google.cloud import firestore
from google.cloud import aiplatform
from datetime import datetime, timezone, timedelta
import vertexai
import functools
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from vertexai.preview.language_models import TextEmbeddingModel
from encryption import get_encryption_service
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint
from google.cloud.aiplatform import MatchingEngineIndex  
from google.cloud.aiplatform_v1.types import IndexDatapoint
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace

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

import firebase_admin
from firebase_admin import auth

try:
    firebase_admin.initialize_app()
    logger.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
    logger.error(traceback.format_exc())

try:
    encryption_service = get_encryption_service()
    logger.info("Encryption service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize encryption service: {e}")
    encryption_service = None

# CONFIG: Updated model configuration for Gemini
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT") or "genai-bot-kdf"
REGION = os.environ.get("REGION", "asia-south1")

LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")

# Vector Search Configuration
VECTOR_SEARCH_ENDPOINT_ID = os.environ.get("VECTOR_SEARCH_ENDPOINT_ID")
DEPLOYED_INDEX_ID = os.environ.get("DEPLOYED_INDEX_ID", "chatbot_memories_deployed")
VECTOR_SEARCH_INDEX_ID = os.environ.get("VECTOR_SEARCH_INDEX_ID")

logger.info(f"Vector Search Config:")
logger.info(f"   ENDPOINT_ID: {VECTOR_SEARCH_ENDPOINT_ID}")
logger.info(f"   DEPLOYED_INDEX_ID: {DEPLOYED_INDEX_ID}")
logger.info(f"Starting chatbot with config:")
logger.info(f"   PROJECT_ID: {PROJECT_ID}")
logger.info(f"   REGION: {REGION}")
logger.info(f"   LLM_MODEL: {LLM_MODEL}")
logger.info(f"   EMBEDDING_MODEL: {EMBEDDING_MODEL}")

try:
    aiplatform.init(project=PROJECT_ID, location=REGION)
    logger.info("Vertex AI initialized successfully")

    db = firestore.Client(project=PROJECT_ID)
    logger.info("Firestore client initialized successfully")

except Exception as e:
    logger.critical(f"FATAL: Failed to initialize Google Cloud services: {e}")
    logger.critical(traceback.format_exc())

# Initialize Vector Search endpoint
vector_search_endpoint = None
if VECTOR_SEARCH_ENDPOINT_ID:
    try:
        vector_search_endpoint = MatchingEngineIndexEndpoint(
            index_endpoint_name=VECTOR_SEARCH_ENDPOINT_ID
        )
        logger.info(f"✓ Vertex AI Vector Search endpoint initialized successfully")
        
    except Exception as e:
        logger.error(f"✗ Failed to initialize Vector Search endpoint: {e}")
        logger.error("Vector Search will be unavailable")
else:
    logger.warning("VECTOR_SEARCH_ENDPOINT_ID not set - Vector Search disabled")

logger.info(f"DEBUG: PROJECT_ID = {PROJECT_ID}")
logger.info(f"DEBUG: VECTOR_SEARCH_INDEX_ID = {VECTOR_SEARCH_INDEX_ID}")
logger.info(f"DEBUG: Building index_name...")

# Initialize Vector Search index for upserts
matching_engine_index = None
if VECTOR_SEARCH_INDEX_ID:
    try:
        index_name = f"projects/{PROJECT_ID}/locations/{REGION}/indexes/{VECTOR_SEARCH_INDEX_ID}"
        matching_engine_index = MatchingEngineIndex(index_name=index_name)
        logger.info(f"✓ Vertex AI Vector Search index initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Vector Search index: {e}")
        logger.error("Vector Search upserts will be unavailable")
else:
    logger.warning("VECTOR_SEARCH_INDEX_ID not set - Vector Search upserts disabled")
    
app = Flask(__name__)

CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"]
}})

def get_user_key():
    """
    Custom key function for rate limiting.
    Uses the user_id if the endpoint is protected by @token_required,
    otherwise falls back to the remote IP address for public endpoints.
    """
    # Check if the @token_required decorator has run and set the user_id
    if hasattr(request, 'user_id') and request.user_id:
        return request.user_id
    
    # Fallback for unprotected routes
    return get_remote_address()

limiter = Limiter(
    app=app,
    key_func=get_user_key,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Validation Schemas
class ConsentSchema(Schema):
    user_id = fields.String(required=False)
    consent = fields.Boolean(allow_none=True)
    username = fields.String(required=True)

class MessageSchema(Schema):
    session = fields.String(required=True)
    messages = fields.List(fields.Dict(), required=True)
    sessionInfo = fields.Dict(required=True)

class DeleteMemoriesSchema(Schema):
    user_id = fields.String(required=True)

# Error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({
        "error": "Validation error",
        "details": error.messages
    }), 400

@app.errorhandler(429)
def handle_rate_limit_error(error):
    return jsonify({
        "error": "Rate limit exceeded",
        "retry_after": error.description
    }), 429

@app.route("/debug/token", methods=["POST"])
def debug_token():
    """Debug endpoint to test token verification without creating profiles"""
    try:
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(' ')[1]
            except IndexError:
                return jsonify({"error": "Invalid Authorization header format"}), 400

        if not token:
            return jsonify({"error": "No token provided"}), 400

        decoded_token = auth.verify_id_token(token)
        
        return jsonify({
            "success": True,
            "uid": decoded_token['uid'],
            "token_info": {
                "iss": decoded_token.get('iss'),
                "aud": decoded_token.get('aud'),
                "auth_time": decoded_token.get('auth_time'),
                "provider": decoded_token.get('firebase', {}).get('sign_in_provider')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Debug token verification failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 400

from functools import wraps

def token_required(f):
    """Decorator to protect endpoints with Firebase ID token verification."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(' ')[1]
            except IndexError:
                return jsonify({"error": "Invalid Authorization header format"}), 401

        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        try:
            decoded_token = auth.verify_id_token(token)
            request.user_id = decoded_token['uid']
            logger.info(f"Token verified successfully for UID: {request.user_id}")
        except auth.ExpiredIdTokenError:
            return jsonify({"error": "Token has expired"}), 401
        except auth.InvalidIdTokenError as e:
            logger.error(f"Invalid token error: {e}")
            return jsonify({"error": "Invalid authorization token"}), 401
        except Exception as e:
            logger.error(f"An unexpected error occurred during token verification: {e}")
            return jsonify({"error": "Could not verify token"}), 500

        return f(*args, **kwargs)
    return decorated_function

def format_time_delta(timestamp_str):
    """Converts an ISO format timestamp string to a relative time string."""
    if not timestamp_str:
        return ""
    try:
        event_time = datetime.fromisoformat(timestamp_str)
        current_time = datetime.now(timezone.utc)
        delta = current_time - event_time

        seconds = delta.total_seconds()
        if seconds < 120:
            return "(just now)"
        elif seconds < 3600:
            return f"({int(seconds / 60)} minutes ago)"
        elif seconds < 86400:
            return f"({int(seconds / 3600)} hours ago)"
        elif seconds < 2592000:
            return f"({int(seconds / 86400)} days ago)"
        else:
            return f"({int(seconds / 2592000)} months ago)"
    except (ValueError, TypeError):
        return ""

@app.route("/login", methods=["POST"])
@token_required
def login():
    """
    Called after a client gets an ID token.
    Verifies token, finds user profile, creates one if it doesn't exist,
    and returns the profile.
    """
    try:
        user_id = request.user_id
        logger.info(f"Processing login for user_id: {user_id}")
        
        user_profile = get_user_profile(user_id)
        
        if user_profile:
            logger.info(f"Found existing profile for {user_id}")
            return jsonify(user_profile), 200
        
        logger.info(f"No profile found for UID {user_id}, creating one.")
        
        try:
            firebase_user = auth.get_user(user_id)
            logger.info(f"Retrieved Firebase user info for {user_id}")
            
            is_anonymous = len(firebase_user.provider_data) == 0
            logger.info(f"User {user_id} is anonymous: {is_anonymous}")
            
            if is_anonymous:
                new_profile = {
                    "username": "Guest User",
                    "email": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "consent": None,
                    "is_anonymous": True,
                    "current_stage": "Stage 1: Relationship Building" # <-- NEW
                }
            else:
                new_profile = {
                    "username": firebase_user.display_name or firebase_user.email or "User",
                    "email": firebase_user.email,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "consent": None,
                    "is_anonymous": False,
                    "current_stage": "Stage 1: Relationship Building" # <-- NEW
                }
            
        except auth.UserNotFoundError:
            logger.warning(f"User {user_id} not found in Firebase Auth, creating anonymous profile")
            new_profile = {
                "username": "Guest User",
                "email": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "consent": None,
                "is_anonymous": True,
                "current_stage": "Stage 1: Relationship Building" # <-- NEW
            }
        except Exception as auth_error:
            logger.error(f"Error getting Firebase user info for {user_id}: {auth_error}")
            logger.error(traceback.format_exc())
            new_profile = {
                "username": "Guest User",
                "email": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "consent": None,
                "is_anonymous": True,
                "current_stage": "Stage 1: Relationship Building" # <-- NEW
            }
        
        logger.info(f"Creating profile for {user_id}: {new_profile}")
        
        upsert_user_profile(user_id, new_profile)
        logger.info(f"Profile saved for {user_id}")
        
        user_profile = get_user_profile(user_id)
        if not user_profile:
            logger.error(f"Failed to retrieve saved profile for {user_id}")
            return jsonify({"error": "Failed to create user profile"}), 500
            
        logger.info(f"Login successful for UID {user_id}")
        return jsonify(user_profile), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in login endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred during login."}), 500

def sanitize_collection_name(user_id):
    """Sanitize user_id to be valid Firestore collection name"""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"user_{sanitized}"
    if not sanitized:
        sanitized = "anonymous_user"
    logger.debug(f"Sanitized user_id '{user_id}' to '{sanitized}'")
    return sanitized

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

    # Test Vertex AI Vector Search
    try:
        if vector_search_endpoint and DEPLOYED_INDEX_ID:
            test_vec = embed_texts(["health check test"])[0].tolist()
            response = vector_search_endpoint.find_neighbors(
                deployed_index_id=DEPLOYED_INDEX_ID,
                queries=[test_vec],
                num_neighbors=1
            )
            health_status["services"]["vertex_ai_vector_search"] = "OK"
            logger.info("Vertex AI Vector Search health check passed")
        else:
            health_status["services"]["vertex_ai_vector_search"] = "NOT_CONFIGURED"
            logger.info("Vector Search not configured")
    except Exception as e:
        health_status["services"]["vertex_ai_vector_search"] = f"ERROR: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error(f"Vertex AI Vector Search health check failed: {e}")
    
    # Test Vertex AI Text Generation
    try:
        test_models = ["gemini-2.5-flash"]
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
            global LLM_MODEL
            LLM_MODEL = working_model
            
    except Exception as e:
        health_status["services"]["vertex_ai_generation"] = f"ERROR: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error(f"Vertex AI text generation health check failed: {e}")
    
    try:
        if encryption_service:
            test_text = "health check test"
            encrypted = encryption_service.encrypt(test_text)
            decrypted = encryption_service.decrypt(encrypted)
            
            if decrypted == test_text:
                health_status["services"]["encryption"] = "OK"
                logger.info("Encryption service health check passed")
            else:
                health_status["services"]["encryption"] = "ERROR: Decryption mismatch"
                health_status["status"] = "unhealthy"
        else:
            health_status["services"]["encryption"] = "WARNING: Service not initialized"
    except Exception as e:
        health_status["services"]["encryption"] = f"ERROR: {str(e)}"
        health_status["status"] = "unhealthy"
        logger.error(f"Encryption health check failed: {e}")
    
    return jsonify(health_status), 200 if health_status["status"] == "healthy" else 503

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

def embed_texts(texts):
    try:
        logger.debug(f"Embedding {len(texts)} texts")
        logger.debug(f"Texts preview: {[t[:50] + '...' if len(t) > 50 else t for t in texts]}")
        
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

def generate_text_with_model(prompt, model_name=None, max_output_tokens=300, temperature=0.2, system_instruction=None):
    try:
        if model_name is None:
            model_name = LLM_MODEL

        logger.debug(f"Generating text with model: {model_name} using the GenerativeModel SDK")
        logger.debug(f"Prompt preview: {prompt[:200]}...")

        # --- FIX: Pass system_instruction to the model constructor ---
        model = GenerativeModel(model_name, system_instruction=system_instruction)
        
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=max_output_tokens
        )
        
        # The prompt is now correctly treated as just the user content
        response = model.generate_content(
        contents=[prompt],
        generation_config=generation_config
        )

        logger.debug(f"Raw response from {model_name}: {response}")
        
        result = response.text
        logger.debug(f"Generated text: {result[:100]}...")
        return result

    except Exception as e:
        logger.error(f"Error generating text with {model_name}: {e}")
        logger.error(traceback.format_exc())
        raise

def generate_text(prompt, max_output_tokens=300, temperature=0.2, system_instruction=None):
    """Main text generation function with fallback models"""
    fallback_models = [
        LLM_MODEL,
        "gemini-2.5-flash",
    ]
    
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
                temperature=temperature,
                system_instruction=system_instruction  # <-- FIX: Pass the argument through
            )
            if result and result.strip():
                return result        
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue
    
    logger.error("All models failed to generate text")
    return "I'm having trouble generating a response right now. Please try again in a moment."

def get_user_profile(user_id):
    """
    Get user profile and decrypt PII fields.
    """
    try:
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Getting user profile for: {user_id} (sanitized: {sanitized_user_id})")
        
        doc_ref = db.collection("users").document(sanitized_user_id)
        doc = doc_ref.get()

        if doc.exists:
            doc_data = doc.to_dict()
            logger.debug(f"Found user document: {doc_data}")
            
            if 'profile' not in doc_data:
                doc_data['profile'] = {}
            
            # --- NEW: Set default stage if missing ---
            if 'current_stage' not in doc_data.get('profile', {}):
                doc_data['profile']['current_stage'] = 'Stage 1: Relationship Building'
            # --- END NEW ---

            if encryption_service and doc_data.get('profile'):
                sensitive_fields = ['username', 'email', 'user_instructions']
                try:
                    doc_data['profile'] = encryption_service.decrypt_dict(
                        doc_data['profile'], 
                        sensitive_fields
                    )
                    logger.debug("Profile data decrypted")

                    # --- ADD THIS DESERIALIZATION LOGIC ---
                    if 'user_instructions' in doc_data['profile']:
                        instructions_val = doc_data['profile']['user_instructions']
                        if isinstance(instructions_val, str) and instructions_val.startswith('['):
                            try:
                                logger.debug("Deserializing user_instructions string back to list.")
                                doc_data['profile']['user_instructions'] = json.loads(instructions_val)
                            except json.JSONDecodeError:
                                logger.error("Failed to decode user_instructions JSON, defaulting to empty list.")
                                doc_data['profile']['user_instructions'] = []
                        elif instructions_val is None:
                             doc_data['profile']['user_instructions'] = []
                        elif not isinstance(instructions_val, list):
                            logger.warning(f"user_instructions is an unexpected type ({type(instructions_val)}), defaulting to empty list.")
                            doc_data['profile']['user_instructions'] = []
                    # --- END ---

                except Exception as e:
                    logger.error(f"Profile decryption error: {e}")
            
            return doc_data
        else:
            logger.debug(f"No profile found for user: {user_id}")
            return None
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        logger.error(traceback.format_exc())
        return None

def upsert_user_profile(user_id, profile_data):
    """
    Upsert user profile with encryption for PII fields.
    """
    try:
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Upserting profile for {user_id}: {profile_data}")

        sensitive_fields = ['username', 'email', 'user_instructions']
        
        # --- NEW: Create a copy for encryption ---
        # This preserves all fields in the original profile_data map
        profile_data_to_encrypt = profile_data.copy()
        
        # --- FIX: Pop non-sensitive fields from the copy, not the original ---
        if 'current_stage' in profile_data_to_encrypt:
            profile_data_to_encrypt.pop('current_stage')
        if 'updated_at' in profile_data_to_encrypt:
             profile_data_to_encrypt.pop('updated_at')
        if 'created_at' in profile_data_to_encrypt:
            profile_data_to_encrypt.pop('created_at')
        if 'consent' in profile_data_to_encrypt:
            profile_data_to_encrypt.pop('consent')
        if 'is_anonymous' in profile_data_to_encrypt:
            profile_data_to_encrypt.pop('is_anonymous')
        # --- END FIX ---
            
        if encryption_service:
            try:
                # --- ADD THIS SERIALIZATION LOGIC ---
                if 'user_instructions' in profile_data_to_encrypt and isinstance(profile_data_to_encrypt['user_instructions'], list):
                    logger.debug("Serializing user_instructions list to JSON string for encryption.")
                    profile_data_to_encrypt['user_instructions'] = json.dumps(profile_data_to_encrypt['user_instructions'])
                # --- END ---

                # Encrypt the sensitive fields
                encrypted_data = encryption_service.encrypt_dict(profile_data_to_encrypt, sensitive_fields)
                
                # --- NEW: Update the original map, don't replace it ---
                # This merges the new encrypted fields back into the original map,
                # preserving fields like 'updated_at'.
                profile_data.update(encrypted_data)
                
                logger.debug("Profile data encrypted and merged")
            except Exception as e:
                logger.error(f"Profile encryption error: {e}")
                logger.warning("Storing profile without encryption")
        
        doc_data = {
            "profile": profile_data
        }
        
        doc_ref = db.collection("users").document(sanitized_user_id)
        current_doc = doc_ref.get()
        
        if current_doc.exists:
            current_data = current_doc.to_dict()
            if 'profile' in current_data:
                # Update the existing profile with our new (partial) data
                current_data['profile'].update(profile_data)
            else:
                current_data['profile'] = profile_data
            doc_data = current_data

        logger.debug(f"Final document structure to upsert: {doc_data}")
        doc_ref.set(doc_data, merge=True)
        
        logger.debug(f"Profile upserted successfully for {user_id}")

    except Exception as e:
        logger.error(f"Error upserting user profile: {e}")
        logger.error(traceback.format_exc())
        raise

def save_memory(user_id, summary_text, metadata=None):
    """
    Save memory with encrypted summary to Firestore
    and send the embedding to Vertex AI Vector Search.
    """
    try:
        if metadata is None:
            metadata = {}
        
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Saving memory for {user_id} (sanitized: {sanitized_user_id})")
        
        created_at = datetime.now(timezone.utc).isoformat()
        
        # 1. Generate embedding from PLAINTEXT
        vec = embed_texts([summary_text])[0].tolist()
        logger.debug(f"Generated embedding from plaintext (dim: {len(vec)})")
        
        # 2. Encrypt the summary text
        encrypted_summary = summary_text
        is_encrypted = False
        
        if encryption_service:
            try:
                encrypted_summary = encryption_service.encrypt(summary_text)
                if encrypted_summary:
                    is_encrypted = True
            except Exception as e:
                logger.error(f"Encryption error: {e}")
        
        # 3. Use timestamp-based ID for memory documents
        memory_id = f"mem_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        # 4. Create the Firestore document WITHOUT embedding array
        mem_doc = {
            "user_id": user_id,
            "summary": encrypted_summary,
            "summary_encrypted": is_encrypted,
            "metadata": metadata,
            "created_at": created_at
        }
        
        # 5. Save metadata to Firestore
        mem_ref = db.collection("users").document(sanitized_user_id).collection("memories").document(memory_id)
        mem_ref.set(mem_doc)
        logger.debug(f"✓ Memory metadata saved to Firestore: {memory_id}")

        # 6. Upsert the vector to Vertex AI Vector Search
        # 6. Upsert the vector to Vertex AI Vector Search
        if matching_engine_index:
            try:
                user_restriction = IndexDatapoint.Restriction(
                    namespace="user_id",
                    allow_list=[sanitized_user_id]
                )

                datapoint = IndexDatapoint(
                    datapoint_id=memory_id,
                    feature_vector=vec,
                    restricts=[user_restriction]
                )
                
                # Use MatchingEngineIndex for upserts
                matching_engine_index.upsert_datapoints(datapoints=[datapoint])
                logger.debug(f"✓ Vector for memory {memory_id} upserted to Vertex AI")
            except Exception as ve:
                logger.error(f"✗ Failed to upsert vector for {memory_id}: {ve}")
                logger.error(traceback.format_exc())
                logger.error("Memory saved to Firestore but not to Vector Search")
        else:
            logger.warning(f"Vector Search not available - memory {memory_id} saved only to Firestore")

        logger.debug(f"Memory saved successfully: {memory_id} (encrypted: {is_encrypted})")
        return True
        
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        logger.error(traceback.format_exc())
        return False

def retrieve_similar_memories(user_id, query_text, top_k=3):
    """
    Retrieve similar memories from Vertex AI Vector Search
    and hydrate them with data from Firestore.
    """
    try:
        sanitized_user_id = sanitize_collection_name(user_id)
        logger.debug(f"Retrieving similar memories for {user_id} (sanitized: {sanitized_user_id})")
        
        # Require Vector Search to be available
        if not vector_search_endpoint:
            logger.error("Vector Search is not available - cannot retrieve memories")
            return []
        
        # Generate query embedding
        q_vec = embed_texts([query_text])[0].tolist()
        
        logger.debug(f"Querying Vector Search endpoint with top_k={top_k}")
        
        # Create namespace filter
        query_filter = [Namespace(
            name="user_id",
            allow_tokens=[sanitized_user_id],
            deny_tokens=[]
        )]
        
        # Query Vector Search with user-specific filtering
        response = vector_search_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[q_vec],
            num_neighbors=top_k,
            filter=query_filter
        )

        if not response or not response[0]:
            logger.debug("Vector Search returned no neighbors")
            return []

        # Get the IDs and distances of the neighbors
        neighbor_ids = [n.id for n in response[0]]
        neighbor_distances = [n.distance for n in response[0]]
        
        logger.debug(f"Vector Search found {len(neighbor_ids)} neighbors")
        for i, (nid, dist) in enumerate(zip(neighbor_ids, neighbor_distances)):
            logger.debug(f"  #{i+1}: {nid} (distance: {dist:.4f})")

        # Hydrate the results from Firestore
        mem_collection_ref = db.collection("users").document(sanitized_user_id).collection("memories")
        doc_refs = [mem_collection_ref.document(mem_id) for mem_id in neighbor_ids if mem_id]
        
        if not doc_refs:
            return []

        # Batch get for efficiency
        docs = db.get_all(doc_refs)
        
        results = []
        for doc in docs:
            if not doc.exists:
                logger.warning(f"Memory ID {doc.id} found in Vector Search but not in Firestore (may have been deleted)")
                continue
                
            data = doc.to_dict()
            
            # Decrypt summary if encrypted
            if data.get("summary_encrypted"):
                if encryption_service:
                    try:
                        decrypted_summary = encryption_service.decrypt(data.get("summary", ""))
                        if decrypted_summary:
                            data["summary"] = decrypted_summary
                        else:
                            logger.warning(f"Failed to decrypt summary for doc {doc.id}")
                    except Exception as e:
                        logger.error(f"Decryption error for doc {doc.id}: {e}")
                else:
                    logger.warning(f"Cannot decrypt doc {doc.id}: encryption service unavailable")
            
            results.append(data)
        
        logger.debug(f"✓ Returning {len(results)} hydrated and decrypted memories from Vector Search")
        return results
        
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        logger.error(traceback.format_exc())
        return []

def summarize_conversation(user_text, assistant_text):
    try:
        logger.debug("Summarizing and evaluating the latest exchange.")
        
        # --- NEW: System instruction defines the AI's task ---
        system_instruction = (
            "You are a data analysis AI. Your task is to analyze a user-assistant exchange and extract three pieces of information.\n\n"
            "**Instructions:**\n"
            "1.  **Significance Decision:** On the first line, write 'SIGNIFICANT: YES' if the user **introduces a new important topic...** or reveals a specific goal. Write 'SIGNIFICANT: NO' only for simple greetings...\n"
            "2.  **Summary:** On the next line, write 'SUMMARY:' followed by a concise, factual, third-person summary...\n"
            "3.  **Instruction Extraction:** On the third line, check if the user gave a direct, explicit instruction for the assistant's future behavior (e.g., 'Always call me...', 'Never mention...').\n"
            "    - If an instruction is found, write 'INSTRUCTION:' followed by a very brief version of that rule (e.g., 'INSTRUCTION: User wants to be called \'Captain\'.', 'INSTRUCTION: Do not suggest mindfulness exercises.').\n"
            "    - If no instruction is found, you MUST write 'INSTRUCTION: NONE'.\n\n"
            "You will be given the exchange to analyze. Provide only the analysis."
        )
        
        # --- NEW: Prompt is now just the data to be analyzed ---
        prompt = (
            f"**Exchange to Analyze:**\nUser: {user_text}\nAssistant: {assistant_text}\n\n"
            "**Your Analysis:**"
        )
        
        # --- NEW: Updated call to generate_text ---
        analysis_text = generate_text(
            prompt, 
            system_instruction=system_instruction, 
            max_output_tokens=200, 
            temperature=0.1
        )
        
        lines = analysis_text.strip().split('\n')
        is_significant = False
        summary = "No summary generated."
        instruction = None

        if lines:
            if "yes" in lines[0].lower():
                is_significant = True
            
            summary_line = next((line for line in lines if "summary:" in line.lower()), None)
            if summary_line:
                summary = summary_line.split(":", 1)[1].strip()

            instruction_line = next((line for line in lines if "instruction:" in line.lower()), None)
            if instruction_line:
                instruction_text = instruction_line.split(":", 1)[1].strip()
                if "none" not in instruction_text.lower():
                    instruction = instruction_text

        logger.debug(f"Significance: {is_significant}, Summary: {summary[:100]}..., Instruction: {instruction}")
        
        return {
            "is_significant": is_significant,
            "summary": summary,
            "instruction": instruction
        }
            
    except Exception as e:
        logger.error(f"Error summarizing exchange: {e}")
        logger.error(traceback.format_exc())
        return {
            "is_significant": False,
            "summary": "Error generating summary",
            "instruction": None
        }

# --- NEW: TTM/CBT System Prompt Template ---
# --- NEW: TTM/CBT System Prompt Template ---
SERENA_SYSTEM_PROMPT_TEMPLATE = (
    "# Persona\n"
    "Your name is Serena , an AI assistant designed to support users with their mental health. "
    "Your primary goal is to be a supportive, validating, and non-judgemental "
    "listener who helps users feel heard.\"\n\n"
    "# Core principles of the conversation:\n"
    "* All the responses you give should be in accordance with the feelings under the Cognitive behaviour therapy.\n"
    "* Always note that you have to validate the stage of the conversation between you and the user.\n"
    "* I’ll give you guidance on how to respond to any question based on different stage.\n"
    "* These are the stages according to the The Transtheoretical Model (TTM) also Stages of Change Theory.\n\n"
    "\n"

    "# TTM Stage-Based Directives\n\n"
    "## Stage1- Relationship Building\n"
    "you have to create a positive welcoming and trust environment with the user.\n"
    "Connection is our primary key as you are an mental health chatbot.\n"
    "Primary goal here will be making the user feel heard, validating the user is also necessary here.\n\n"
    
    "## Stage 2- Assessing the user concern\n"
    "From your side as Serena you start exploring the depth of the user problem, "
    "evaluate the root cause through few queries to the user asking for the context, "
    "what do they go through, history of any trauma occurrences. \n"
    "Remember to do all these with user consent.\n"
    "Get all the details of the issues with clarity and ask for acknowledgement that what u understood is right or not. \n"
    "Don’t bombard with questions, keep it simple but gather maximum details. \n"
    "From the user side this stage is where he/she opens up and they should feel validated and being understood here.\n\n"
    
    "## Stage 3- Goal setting\n"
    "here from your side as Serena, "
    "you should focus on transforming the problem into some goal to overcome it, "
    "where you can ask users for what they wanna do with the problem, "
    "try to retrieve it from the older info shared or ask the user directly. \n"
    "Give realistic solution to their problem, "
    "before giving this suggestion ensure once the user will be in a state to accept and implement it basically assess their commitment level and then come to a conclusion if this plan will workout for the user . \n"
    "From the user side, they must feel that you have understood their feeling and that ur trying to fight and solve the issue along with the user like a friend, a comrade.\n\n"
    
    "## Stage 4 – Intervention and Work\n"
    "So here you have to actually give techniques to overcome "
    "the problem these should be evidence based therapeutic techniques like the ones I gave like Cognitive Behaviour therapy, "
    "psychodynamic theories. If needed give set of instructions along with it to continue practising the technique in a long term. \n"
    "Maybe educate a little on why they are feeling so, what is the main cause and what can be done. \n"
    "From the user side , they should be provided with solutions, a clear plan, psychoeducation on what I said earlier. \n"
    "This should assure them that this solution can be overcomed and can be got ridden of in sometime and they’re not alone facing this problem.\n\n"
    
    "## Stage 5- Termination & Follow-Up\n"
    "Here you should be concluding this conversation on a positive motivating tone, and ask them to reach out again if they felt the same emotions. \n"
    "Ensure them that you will be there for the user in the future too and give a time frame to reflect back. \n"
    "If the user returns back after certain time, just check up on them on their level of recovery.\n\n"
    
    "# Important Functionality- Memory Usage Protocol:\n"
    "If retrieved memories are provided, first analyze them to understand the user's usual behavior, "
    "preferences, and dislikes.\n"
    "Then, seamlessly weave specific details from these memories into your response to show you remember their context.\n\n"
    
    """
    ## Transition Rules:

    * **From Stage 1 to Stage 2:**
        * **Trigger:** When the user moves past the initial greeting and shares a specific feeling, problem, or reason for talking.

    * **From Stage 2 to Stage 3:**
        * **Trigger:** When you have gathered enough context about the user's problem, you've summarized it, and the user has *confirmed* your understanding.

    * **From Stage 3 to Stage 4:**
        * **Trigger:** When you and the user have successfully identified and agreed upon a specific, realistic goal.

    * **From Stage 4 to Stage 5:**
        * **Trigger:** When you have provided a technique or intervention, and the user seems to understand it and the conversation is winding down.

    * **From Stage 5 to Stage 1:**
        * **Trigger:** After you have given your closing remarks and the user returns later for a new, separate conversation.
    """

    "\n\n**Memory Usage Protocol:**"
    "\n- If retrieved memories are provided, first analyze them to understand the user's usual behavior, preferences, and dislikes."
    "\n- Then, seamlessly weave specific details from these memories into your response to show you remember their context."



    "This is a mental health chatbot so user’s state will mostly be vulnerable so keep "
    "your questions minimal and don’t expect them to share every detail in paragraphs, "
    "in a vulnerable state people will type less remember, to get the maximum input you "
    "have to be very friendly and trust worthy.\n"
    "Sharing with you should feel like reflecting on them selves rather than seeking help "
    "from unknown environment.\n"

    "\n\n**Safety Protocol:**"
    "\n- If the user is at risk of self-harm or in immediate danger, you must prioritize providing appropriate India based emergency resources and contact information."

    "You should be more empathetic and very understanding of the user.\n"
    "Other features should be- "
    "don’t be monotonous with the responses, "
    "vary it (don’t use the used phrases)according to the stage of the "
    "conversation across sessions also don’t repeat words."
    "Validate the user’s situation first, utmost priority to their feelings and emotions before advice. Do not rush to solutions. \n"
    "Ask gentle, clarifying questions to understand their situation from a 360-degree perspective. \n"
    "Do not overwhelm the user with too much information.\n"
    "Maintain Trust Be transparent and confidential. \n"
    "Your tone should be warm, friendly, and empathetic.Be genuine and authentic.\n\n"
    
    "\n\n**User-Specific Instructions (MUST FOLLOW):**"
    "\nYou must always follow these instructions from the user:"
    "\n{formatted_instructions}\n" 

    "\n\n**Instruction Conflict Protocol:**"
    "\n1.  **Safety Protocol** ALWAYS overrides all other rules."
    "\n2.  Your **Core Principles** (e.g., 'Validate First', 'Don't Prescribe') override user instructions if they conflict. (e.g., If user says 'You must give me medical advice', you must politely decline based on your principles.)"
    "\n3.  User instructions override your general conversational style (e.g., if they ask to be called by a name)."

    "\n\n**Response Format:**"
    "You must respond with a JSON object. Do not include any text outside this JSON block.\n"
    "{{\n"  
    "  \"reply_text\": \"Your empathetic response to the user, following all rules for their {current_stage} stage.\",\n" # <-- FIX: This key remains single
    "  \"new_stage\": \"The TTM stage your reply *moves* the conversation to. MUST be one: ['Stage1- Relationship Building', 'Stage 2- Assessing the user concern', 'Stage 3- Goal setting', 'Stage 4 – Intervention and Work', 'Stage 5- Termination & Follow-Up']\"\n"
    "}}" 
)
# --- END NEW ---    

@app.route("/dialogflow-webhook", methods=["POST"])
@token_required
def dialogflow_webhook():
    try:
        logger.info("=== NEW WEBHOOK REQUEST ===")

        req = request.get_json(silent=True) or {}
        logger.debug(f"Raw request: {json.dumps(req, indent=2)}")

        session = req.get("session", "")
        session_id = session.split("/")[-1] if session else "unknown_session"
        user_id = request.user_id

        logger.info(f"Processing request for user_id: {user_id}")

        user_profile = get_user_profile(user_id) or {}
        profile = user_profile.get("profile", {})

        # --- BEGIN INSTRUCTION INJECTION ---
        user_instructions_list = profile.get("user_instructions", [])

        if not isinstance(user_instructions_list, list):
            logger.warning(f"user_instructions was not a list (type: {type(user_instructions_list)}), attempting to parse or reset.")
            if isinstance(user_instructions_list, str) and user_instructions_list.startswith('['):
                try:
                    user_instructions_list = json.loads(user_instructions_list)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode user_instructions JSON, resetting to empty list for user {user_id}.")
                    user_instructions_list = []
            else:
                logger.warning(f"user_instructions was invalid, resetting to empty list for user {user_id}.")
                user_instructions_list = []

        formatted_instructions = "No specific instructions on file."
        if user_instructions_list:
            formatted_instructions = "\n".join([f"- {inst}" for inst in user_instructions_list])
        # --- END INSTRUCTION INJECTION ---

        user_text = ""
        for m in req.get("messages", []):
            if m.get("text"):
                user_text = m["text"].get("text", [""])[0]
                break
        if not user_text:
            user_text = req.get("text", "") or "Hello"

        logger.info(f"User message: '{user_text}'")
        
        has_consent = profile.get("consent", False)
        logger.info(f"User consent status: {has_consent}")

        retrieved_text = ""
        if has_consent:
            logger.info("Retrieving similar memories...")
            retrieved = retrieve_similar_memories(user_id, user_text, top_k=3)
            
            if retrieved:
                memory_lines = []
                for r in retrieved:
                    summary = r.get('summary', 'No summary available.')
                    time_ago = format_time_delta(r.get('created_at')) 
                    memory_lines.append(f"- {summary} {time_ago}")
                retrieved_text = "\n".join(memory_lines)
                logger.info(f"Found {len(retrieved)} relevant memories with time context.")
            else:
                retrieved_text = "No relevant memories found."
        else:
            retrieved_text = "Memory retrieval is disabled for this user."

        # --- NEW: Time Context and Stage Reset Logic ---
        time_context = ""
        current_stage = profile.get("current_stage", "Stage 1: Relationship Building")
        logger.info(f"Stage loaded from profile: {current_stage}")
        
        try:
            last_seen_str = profile.get("updated_at")
            if last_seen_str:
                last_interaction_time = datetime.fromisoformat(last_seen_str)
                time_delta = datetime.now(timezone.utc) - last_interaction_time
                
                # If last interaction was over 24 hours ago, reset stage
                if time_delta > timedelta(hours=24):
                    time_ago_str = format_time_delta(last_seen_str).strip('()')
                    time_context = f"Note to AI: The user's last interaction was {time_ago_str}. Acknowledge this pause and re-establish rapport."
                    current_stage = "Stage 1: Relationship Building"
                    logger.info(f"User inactive for {time_delta}. Forcing reset to Stage 1.")
                
                # If over 15 mins but less than 24h, just add time context
                elif time_delta > timedelta(minutes=15):
                    time_ago_str = format_time_delta(last_seen_str).strip('()')
                    time_context = f"Note to AI: The user's last interaction was {time_ago_str}. Acknowledge this pause."
                    logger.info(f"Generated time context: {time_context}")

        except Exception as e:
            logger.warning(f"Could not analyze user profile timestamp for time_context: {e}")
        # --- END NEW ---

        session_params = req.get("sessionInfo", {}).get("parameters", {})
        short_term_memory = json.dumps(session_params) if session_params else "No session parameters."
        logger.debug(f"Short-term session memory: {short_term_memory}")

        
        # --- NEW: Build System Instruction and Prompt ---
        
        # Build the final system instruction from the global template
        system_instruction = SERENA_SYSTEM_PROMPT_TEMPLATE.format(
            formatted_instructions=formatted_instructions,
            current_stage=current_stage
        )
        
        # Build the dynamic user prompt
        prompt = (
            "# --- CONTEXT FOR THIS RESPONSE ---\n\n"
            f"[Time Context]\n{time_context}\n\n"
            f"[Current Stage]\n{current_stage}\n\n"
            f"[Short-Term Session Memory]\n{short_term_memory}\n\n" 
            f"[Retrieved Memories (Long-Term)]\n{retrieved_text}\n\n" 
            f"\n--- END CONTEXT ---"
            f"\n\nUser: {user_text}\n\n"
            "**AI, provide your JSON response:**"
        )
        # --- END NEW ---


        logger.info("Generating response... (Call 1)")
        
        # --- NEW: Updated call to generate_text ---
        raw_response_text = generate_text(
            prompt, 
            system_instruction=system_instruction, 
            max_output_tokens=2500, 
            temperature=0.7
        ).strip()

        # --- NEW: Parse JSON response from Call 1 ---
        logger.debug(f"Raw response JSON: {raw_response_text}")
        reply_text = "I'm having a little trouble thinking right now. Could you try that again?"
        new_stage = current_stage # Default to old stage on error
        
        try:
            json_match = re.search(r'\{.*\}', raw_response_text, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group(0))
                reply_text = response_json.get("reply_text", reply_text)
                new_stage = response_json.get("new_stage", current_stage)
                logger.info(f"Parsed reply: '{reply_text[:100]}...'")
                logger.info(f"Parsed new_stage: '{new_stage}'")
            else:
                logger.error("No JSON found in main response, using fallback.")
                reply_text = raw_response_text # Use raw text if it wasn't JSON
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse main response JSON: {e}")
            if "reply_text" in raw_response_text:
                 reply_text = "There was a small error in my response structure, but here is my reply: " + raw_response_text
            # Fallback to default error message
        # --- END NEW ---

        # --- NEW: Prepare profile update with new stage and timestamp ---
        profile_update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "current_stage": new_stage
        }
        # --- END NEW ---

        if has_consent:
            logger.info("Creating and evaluating summary of the current exchange... (Call 2)")
            analysis_result = summarize_conversation(user_text, reply_text)
            
            # --- BEGIN NEW INSTRUCTION-SAVING LOGIC ---
            new_instruction = analysis_result.get("instruction")
            if new_instruction:
                logger.info(f"New user instruction identified: '{new_instruction}'")
                
                if new_instruction not in user_instructions_list:
                    logger.info("Adding new instruction to profile.")
                    user_instructions_list.append(new_instruction)
                    profile_update_data['user_instructions'] = user_instructions_list # Add to the update payload
                else:
                    logger.info("Instruction already exists, not adding duplicate.")
            # --- END NEW INSTRUCTION-SAVING LOGIC ---

            if analysis_result.get("is_significant"):
                summary = analysis_result.get("summary")
                # --- FIX: Check for "No summary generated." instead of "error" ---
                if summary != "No summary generated.": 
                    if save_memory(user_id, summary, {"topic": "conversation_exchange", "session_id": session_id}):
                        logger.info("SIGNIFICANT exchange saved as a new memory.")
                    else:
                        logger.error("Failed to save significant exchange as memory.")
                else:
                    logger.warning("Skipping memory save because no summary was generated (likely not significant or only an instruction was given).")
            else:
                logger.info("Exchange was not significant. Skipping memory save.")
        else:
            logger.info("User has not consented to memory storage - skipping conversation analysis and memory save.")

        # --- NEW: Save profile updates (timestamp, stage, instructions) ---
        try:
            # We use the existing profile data to ensure we don't overwrite anything
            profile.update(profile_update_data)
            upsert_user_profile(user_id, profile)
            logger.info(f"Successfully saved profile updates for {user_id}.")
        except Exception as e:
            logger.error(f"Failed to save profile updates for {user_id}: {e}")
        # --- END NEW ---

        # --- MODIFIED: Add session params to the response ---
        # This sends the short-term memory back to Dialogflow
        response = {
            "fulfillment_response": {
                "messages":[{"text": {"text":[reply_text]}}]
            },
            "session_info": {
                "parameters": session_params
            }
        }
        # --- END MODIFIED ---
        
        logger.info("Request completed successfully")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in dialogflow_webhook: {e}")
        logger.error(traceback.format_exc())
        error_response = {"fulfillment_response": {"messages":[{"text": {"text":["I'm having trouble right now. Please try again in a moment."]}}]}}
        return jsonify(error_response), 500

@app.route("/consent", methods=["POST"])
@token_required
@limiter.limit("20/minute")
def consent():
    try:
        logger.info("=== CONSENT/PROFILE UPDATE REQUEST ===")
        user_id = request.user_id

        payload = request.get_json(silent=True) or {}
        logger.debug(f"Payload: {payload}")
        
        schema = ConsentSchema()
        try:
            payload = schema.load(payload)
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}")
            return jsonify({"error": "Invalid request data", "details": err.messages}), 400

        existing_doc = get_user_profile(user_id)
        if existing_doc is None:
            existing_doc = {}
        
        profile_data = existing_doc.get('profile', {})
        
        profile_data.update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

        if 'consent' in payload:
            profile_data['consent'] = bool(payload['consent'])
            logger.info(f"Updating consent for {user_id}: {profile_data['consent']}")

        if 'username' in payload:
            profile_data['username'] = payload['username']
            logger.info(f"Updating username for {user_id}: {profile_data['username']}")
        
        try:
            logger.info(f"Upserting document for {user_id} with data: {profile_data}")
            upsert_user_profile(user_id, profile_data)
        except Exception as e:
            logger.error(f"Database error updating profile: {e}")
            return jsonify({"error": "Failed to update profile", "details": str(e)}), 500

        updated_profile = get_user_profile(user_id)
        if not updated_profile:
            logger.error(f"Failed to retrieve updated profile for {user_id}")
            return jsonify({"error": "Failed to retrieve updated profile"}), 500
            
        logger.info(f"Profile for {user_id} updated successfully.")
        return jsonify(updated_profile)
    
    except Exception as e:
        logger.error(f"Error in consent/profile endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/delete_memories", methods=["POST"])
@token_required
def delete_memories():
    """
    Delete memories from both Firestore and Vertex AI Vector Search.
    """
    try:
        logger.info("=== DELETE MEMORIES REQUEST ===")
        user_id = request.user_id 
        sanitized_user_id = sanitize_collection_name(user_id)
        
        logger.info(f"Deleting memories for user: {user_id} (sanitized: {sanitized_user_id})")
        
        mems_ref = db.collection("users").document(sanitized_user_id).collection("memories")
        mems = mems_ref.stream()
        
        count = 0
        ids_to_delete = []
        refs_to_delete = []

        for m in mems:
            ids_to_delete.append(m.id)
            refs_to_delete.append(m.reference)
            count += 1
        
        if not ids_to_delete:
            logger.info(f"No memories to delete for {user_id}")
            return jsonify({"ok": True, "deleted": 0})

  
        # 1. Delete from Vertex AI Vector Search
        if matching_engine_index:
            try:
                matching_engine_index.remove_datapoints(
                    datapoint_ids=ids_to_delete
                )
                logger.info(f"✓ Deleted {len(ids_to_delete)} vectors from Vertex AI for user {user_id}")
            except Exception as ve:
                logger.error(f"✗ Failed to delete vectors from Vector Search: {ve}")
                logger.error(traceback.format_exc())
                logger.warning("Continuing with Firestore deletion despite Vector Search error")
        else:
            logger.warning(f"Vector Search not available - skipping vector deletion for {user_id}")

        # 2. Delete from Firestore (using a batch for efficiency)
        batch = db.batch()
        for ref in refs_to_delete:
            batch.delete(ref)
        batch.commit()
        
        logger.info(f"✓ Deleted {count} memories from Firestore for {user_id}")
        return jsonify({"ok": True, "deleted": count})
    
    except Exception as e:
        logger.error(f"Error in delete_memories endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/reset_instructions", methods=["POST"])
@token_required
def reset_instructions():
    """
    Reset user instructions by clearing the user_instructions list from the profile.
    NEW: Also resets the current_stage to Stage 1.
    """
    try:
        logger.info("=== RESET INSTRUCTIONS REQUEST ===")
        user_id = request.user_id
        sanitized_user_id = sanitize_collection_name(user_id)
        
        logger.info(f"Resetting instructions for user: {user_id} (sanitized: {sanitized_user_id})")
        
        # --- NEW: Simplified Logic ---
        # We don't need to get the profile first.
        # Just send the fields we want to change.
        profile_update = {
            'user_instructions': [],
            'current_stage': "Stage 1: Relationship Building",
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # upsert_user_profile is designed to handle partial updates.
        # This will encrypt 'user_instructions' and correctly save 'current_stage'.
        upsert_user_profile(user_id, profile_update)
        
        logger.info(f"✓ Successfully reset instructions and stage for user {user_id}")
        
        # Return the fully updated profile
        updated_profile = get_user_profile(user_id)
        return jsonify(updated_profile), 200
        # --- END NEW ---
    
    except Exception as e:
        logger.error(f"Error in reset_instructions endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

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