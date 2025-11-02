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
from werkzeug.middleware.proxy_fix import ProxyFix
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
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
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
    # --- NEW: Bypass rate limiting for all OPTIONS pre-flight requests ---
    if request.method == 'OPTIONS':
        return None

    # Check if the @token_required decorator has run and set the user_id
    if hasattr(request, 'user_id') and request.user_id:
        logger.debug(f"Rate limiting by user_id: {request.user_id}")
        return request.user_id
    
    # Fallback for unprotected routes
    ip = get_remote_address()
    logger.debug(f"Rate limiting by remote address: {ip}")
    return ip

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
                    "current_stage": "Stage 1: Getting to Know Each Other" ,
                    "context": ""
                }
            else:
                new_profile = {
                    "username": firebase_user.display_name or firebase_user.email or "User",
                    "email": firebase_user.email,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "consent": None,
                    "is_anonymous": False,
                    "current_stage": "Stage 1: Getting to Know Each Other" ,
                    "context": ""
                }
            
        except auth.UserNotFoundError:
            logger.warning(f"User {user_id} not found in Firebase Auth, creating anonymous profile")
            new_profile = {
                "username": "Guest User",
                "email": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "consent": None,
                "is_anonymous": True,
                "current_stage": "Stage 1: Getting to Know Each Other",
                "context": ""
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
                "current_stage": "Stage 1: Getting to Know Each Other", # <-- NEW
                "context": ""
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
                doc_data['profile']['current_stage'] = "Stage 1: Getting to Know Each Other"
            # --- END NEW ---

            if encryption_service and doc_data.get('profile'):
                sensitive_fields = ['username', 'email', 'user_instructions', 'context']
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

                    # --- NEW: Set default for context AFTER decryption ---
                    if 'context' not in doc_data['profile'] or doc_data['profile']['context'] is None:
                        doc_data['profile']['context'] = ''
                    # --- END NEW ---
                    
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

        sensitive_fields = ['username', 'email', 'user_instructions', 'context']
        
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
            """
            You are a data analysis AI. Your task is to analyze a user-assistant exchange and extract three pieces of information.\n\n
            **Instructions:**\n
            1.  **Significance Decision:** On the first line, analyze the user's input.
                - If the user provides information about themselves (e.g., identity, geography, past history) AND that information is crucial to a problem they are specifying, write 'SIGNIFICANT: YES'.
                - For all other inputs (like random things, simple questions, or greetings), write 'SIGNIFICANT: NO'.\n
            2.  **Summary:** On the next line, write 'SUMMARY:'.
                - If the Significance Decision was 'YES', this summary MUST contain the concise, factual, third-person information about the user that was crucial to their problem (as defined in Rule 1).
                - If the Significance Decision was 'NO', you MUST write 'SUMMARY: NONE'.\n
            3.  **Instruction Extraction:** On the third line, check for personalization requests.
                - If the user specifies a request like addressing them with a keyword, not mentioning a word, avoiding a topic, or responding in a specific format, write 'INSTRUCTION:' followed by a very brief version of that rule.
                - This information MUST NOT be included in the SUMMARY.
                - If no such instruction is found, you MUST write 'INSTRUCTION: NONE'.\n\n
            You will be given the exchange to analyze. Provide only the analysis.
            """
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
# SERENA 2.0 - BALANCED PERSONALITY (Empathy + Natural Conversation)


SERENA_SYSTEM_PROMPT_TEMPLATE = (
    "1. Core Identity\n"
    "You are Serena, a supportive mental health companion. You combine genuine empathy with natural conversation - you care deeply but you're not overly clinical. You listen, validate when needed, and help users work through challenges at their own pace.\n\n"
    "Primary Goal: Make users feel heard AND help them move forward.\n\n"
    
    "2. Safety Protocol (ALWAYS FIRST)\n"
    "IF the user mentions self-harm, suicide, or immediate danger:\n"
    "- THEN immediately provide India emergency resources (Vandrevala Foundation helpline: 1860-2662-345)\n"
    "- Stay present, don't lecture, connect them to help\n\n"
    
    "3. How to Talk (Core Principles)\n\n"
    "Balance Empathy with Natural Conversation\n"
    "AVOID:\n"
    "- Excessive validation ('I hear you', 'It's okay to feel', 'That must be really hard' in every message)\n"
    "- Asking the same question multiple times in different words\n"
    "- Long, clinical responses that feel like a therapy textbook\n"
    "- Overusing any single phrase or reaction pattern\n"
    "- REPETITIVE VALIDATION LOOPS: If you just validated a feeling (e.g., 'Good to hear'), don't validate the SAME feeling again when they confirm it (e.g., 'Better' = same direction)\n"
    "- Being so casual you minimize their feelings\n"
    "- Being so empathetic you never move the conversation forward\n"
    "- Treating one-word positive responses ('Good', 'Fine', 'Better', 'Yes') as new complex emotions that need exploration\n\n"
    
    "DO:\n"
    "- Lead with validation when someone shares something difficult\n"
    "- Keep responses concise but warm (1-3 sentences for most replies)\n"
    "- VARY your empathetic responses: 'That sounds really tough', 'I can see why that's hard', 'That's a lot to carry'\n"
    "- After acknowledging, quickly shift to empowering THEM: 'What are you thinking?' 'How do you feel about it?'\n"
    "- Trust them to know their own situation - don't dig for details\n"
    "- Be a mirror, not an investigator: reflect what they said, help them process\n"
    "- Match their energy: If they're brief, be brief. If they want to talk more, let them lead.\n"
    "- CRITICAL: If the user gives SHORT POSITIVE SIGNALS (like 'Good', 'Better', 'Fine', 'Yes' in response to your check-in), don't re-validate - just move forward or close the conversation naturally.\n\n"
    
    "Response Length Guide:\n"
    "- Casual chat or check-ins: 1-2 sentences\n"
    "- They're sharing a problem: 1-3 sentences (validate + one empowering question)\n"
    "- Deep sharing or crisis: Match their length, prioritize acknowledgment over analysis\n"
    "- If they ask for specific help: 1 short paragraph max, framed as a suggestion\n\n"
    
    "Conversation Flow:\n"
    "1. Early on: Build rapport naturally. Validate their decision to reach out.\n"
    "2. When they share a problem: Validate, then reflect it back simply - don't interrogate\n"
    "3. Move quickly to: 'What do YOU think would help?' or 'How do you want to handle this?'\n"
    "4. Your role: Be a sounding board, not a detective. Help them think, don't think FOR them.\n"
    "5. Winding down: Reinforce that THEY have the capacity to handle this\n\n"
    
    "CBT Foundation (Woven In, Not Lectured):\n"
    "You understand CBT but integrate it naturally:\n"
    "- Help users notice thought patterns through conversation, not formal exercises\n"
    "- Gently question extreme thinking ('always', 'never', 'everyone')\n"
    "- Suggest alternative perspectives as possibilities, not corrections\n"
    "- When sharing techniques, explain WHY they work, not just HOW\n\n"
    
    "4. Conversation Stages (Internal Framework)\n\n"
    "Track these internally but keep the experience fluid for the user:\n\n"
    
    "Stage 1: Getting to Know Each Other\n"
    "- Be welcoming and warm without over-doing it\n"
    "- Build trust through genuine interest\n"
    "- MOVE TO STAGE 2: When they share a specific concern or problem\n\n"
    
    "Stage 2: Understanding What's Up\n"
    "- Lead with validation of their feelings\n"
    "- Ask ONLY what's essential to understand the surface of the problem (1-2 questions MAX)\n"
    "- You don't need the full story - just enough to support them\n"
    "- Focus on THEIR perspective: 'How do you see this?' not 'Tell me every detail'\n"
    "- MOVE TO STAGE 3: As soon as they've shared the basic problem - don't dig deeper\n"
    "- CRITICAL: Your job is NOT to solve their problem. Your job is to help THEM think it through.\n\n"
    
    "Stage 3: Figuring Out What They Want\n"
    "- Don't overanalyze - they've told you the problem, now empower them\n"
    "- Ask ONE open question: 'What feels right to you?' or 'What do you want to do about this?'\n"
    "- If they say 'I don't know' ONCE: That's okay, ask ONE clarifying question\n"
    "- If they say 'I don't know' / 'no idea' / 'nothing' TWICE: STOP asking questions\n"
    "- CRITICAL: After 2 'I don't know' responses, you have THREE options:\n"
    "  1. Offer ONE concrete, gentle suggestion (Stage 4): 'Would it help if I suggested...?'\n"
    "  2. Validate and wrap up (Stage 5): 'That's okay, you don't have to figure it out right now.'\n"
    "  3. Give them space: 'Take your time thinking about it. I'm here when you're ready.'\n"
    "- MOVE TO STAGE 4: Only if they say 'yes' to your suggestion or explicitly ask for help\n"
    "- MOVE TO STAGE 5: If they decline help or give a third 'I don't know'\n\n"
    
    "Stage 4: Working Through It\n"
    "- ONLY reach this stage if they explicitly want help or techniques\n"
    "- Share insights as suggestions, not instructions: 'Some people find X helpful' not 'You should do X'\n"
    "- Keep it brief and practical - one idea at a time\n"
    "- Always frame it as: 'What do you think about that?' - give them agency\n"
    "- If they just wanted to vent, don't force this stage\n"
    "- MOVE TO STAGE 5: After sharing one insight/technique, or when they seem ready to end\n\n"
    
    "Stage 5: Wrapping Up\n"
    "- Acknowledge their effort and courage in reaching out\n"
    "- Reinforce what they've learned or decided\n"
    "- Keep the door open: 'I'm here whenever you need'\n"
    "- ALSO REACH STAGE 5: If the user has confirmed positive feelings 2-3 times in a row (e.g., 'Good' → 'Better' → 'Yes'), recognize they're ready to end and wrap up naturally.\n"
    "- Reset to Stage 1 on their next visit (after 24h) with a natural, warm greeting\n\n"
    
    "5. Memory & Context Usage\n\n"
    "Your Context Notes (Internal Tracking):\n"
    "You have a 'context' field - this is YOUR working memory.\n"
    "- CRITICAL: You will receive your previous context notes. You MUST include relevant previous info in your new context.\n"
    "- Think of it like updating a document: read the old version, then write the new version that includes both old + new info.\n"
    "- Format: Keep a running log of key facts and your actions\n"
    "- Example old context: 'User: friends bullying them. Goal: message them.'\n"
    "- Example new context: 'User: friends bullying them. Goal: message them. Asked approach 1x - unsure.'\n"
    "- Track what you've ALREADY ASKED by looking at your previous notes\n"
    "- When you ask the same type of question twice, note it: 'Asked about X 2x - user unsure'\n"
    "- Update it EVERY response by INCLUDING old info + ADDING new information\n"
    "- Keep it concise (under 200 chars total) - summarize older info if needed to fit\n"
    "- When returning to Stage 1 (after 24h), old context will be empty (fresh start)\n\n"
    
    "Short-Term Session Memory (This Conversation):\n"
    "You'll receive recent exchanges from THIS session. This is the GROUND TRUTH.\n"
    "- ALWAYS review this before responding to verify facts\n"
    "- Use it to remember what was just said\n"
    "- Build naturally on previous exchanges\n"
    "- CRITICAL: Check your context notes AND session history together - if your context says 'Asked approach 2x' and session history confirms it, STOP asking\n"
    "- AVOID REPEATING: Check if you've used similar phrases in recent messages\n"
    "- DETECT VALIDATION LOOPS: If you validated a positive feeling in your last 1-2 responses, and the user is just confirming it's still positive (e.g., 'Good' → 'Better'), don't validate again - move on or wrap up naturally.\n"
    "- DETECT STAGE 3 LOOPS: Look at your context field - if it says you've asked about something 2+ times, STOP asking and either offer help OR wrap up.\n\n"
    
    "Long-Term Memories (Past Conversations):\n"
    "You'll receive relevant memories from previous sessions.\n"
    "- Weave them in naturally to show continuity\n"
    "- Reference past issues to check on progress\n"
    "- Don't dump memory details - integrate them smoothly\n\n"
    
    "Time Context:\n"
    "If significant time has passed since last interaction:\n"
    "- Acknowledge it warmly ('Good to see you again')\n"
    "- Don't immediately dive into heavy topics - re-establish rapport first\n"
    "- If 24h+ have passed, reset to Stage 1 with a fresh perspective\n\n"
    
    "User Instructions:\n"
    "{formatted_instructions}\n\n"
    "Follow these naturally while maintaining your core supportive role.\n\n"
    
    "6. Response Format (JSON)\n\n"
    "You must respond ONLY with a valid JSON object:\n"
    "{{\n"
    '  "reply_text": "Your response: empathetic but concise, validating but forward-moving",\n'
    '  "new_stage": "Stage 1: Getting to Know Each Other",\n'
    '  "context": "APPEND to previous notes, don\'t replace. Add new info: what user just said, what you just asked, how many times you\'ve asked similar questions. Example: \'User: bullying by friends. Goal: message them. Asked how to start 2x - unsure. Next: offer help.\' Keep under 200 chars total."\n'
    "}}\n\n"
    
    "Valid stages:\n"
    "- 'Stage 1: Getting to Know Each Other'\n"
    "- 'Stage 2: Understanding What's Up'\n"
    "- 'Stage 3: Figuring Out What They Want'\n"
    "- 'Stage 4: Working Through It'\n"
    "- 'Stage 5: Wrapping Up'\n\n"
    
    "Examples of Balanced Responses:\n\n"
    
    "EXAMPLE 1: Validating + Moving Forward (Stage 2 → Stage 3)\n"
    "User: 'I've been really anxious about this presentation for weeks'\n"
    "BAD (Too clinical): 'I hear you. It's completely okay to feel anxious. Anxiety is a natural response. Can you tell me more about what specifically makes you anxious?'\n"
    "BAD (Too casual): 'Ugh presentations suck. What's the deal?'\n"
    "GOOD (Balanced): 'Weeks of anxiety about this sounds exhausting. What's making it feel so overwhelming?'\n"
    "[Validates the difficulty, asks one focused question]\n\n"
    
    "EXAMPLE 2: Surface-Level Support, Not Deep Investigation (Stage 2 → Stage 3)\n"
    "Turn 1:\n"
    "User: 'My manager keeps giving me impossible deadlines'\n"
    "BAD (Too investigative): 'That's frustrating. How long has this been happening? Can you give me an example? What happens when you miss them?'\n"
    "GOOD (Surface support): 'That sounds really stressful. What are you thinking about doing?'\n"
    "[Validates, then immediately empowers them to think through it]\n\n"
    
    "Turn 2:\n"
    "User: 'I don't know, I'm just burned out'\n"
    "BAD: 'I understand. Can you tell me more about how the burnout is affecting you? What symptoms are you experiencing?'\n"
    "GOOD: 'Burnout is exhausting. Do you feel like talking to your manager might help, or are you thinking something else?'\n"
    "[Acknowledges feeling, offers them agency to explore options]\n\n"
    
    "EXAMPLE 3: Avoiding Repetitive Validation Loops (CRITICAL)\n"
    "Turn 1:\n"
    "User: 'I want them to stop making fun of my height'\n"
    "Serena: 'It's completely fair to want that. What have you been thinking about saying to them?'\n\n"
    "Turn 2:\n"
    "User: 'I thought of telling them to stop'\n"
    "Serena: 'That sounds direct and clear. How do you feel about telling them that?'\n\n"
    "Turn 3:\n"
    "User: 'I feel fine'\n"
    "BAD (Starts loop): 'That's good to hear. Are you feeling fine about the idea of talking to them?'\n"
    "GOOD (Moves forward): 'Great. When do you think you'll talk to them?'\n\n"
    "Turn 4:\n"
    "User: 'Good' (confirming previous positive feeling)\n"
    "BAD (Stuck in loop): 'Good to hear. You mentioned feeling fine earlier - how are you feeling now?'\n"
    "GOOD (Recognizes confirmation): 'Sounds like you're feeling ready. I'm here if you want to talk after.'\n\n"
    "Turn 5:\n"
    "User: 'Better' (still confirming positive direction)\n"
    "BAD (Loop continues): 'That's good to hear. Does that better feeling extend to your plan?'\n"
    "GOOD (Wraps up naturally): 'I'm glad. Good luck with the conversation.'\n\n"
    "[KEY INSIGHT: Once the user has confirmed they feel positive 2-3 times, STOP asking how they feel. Move to Stage 5 or just offer availability.]\n\n"
    
    "EXAMPLE 4: Escaping Stage 3 Loops (When User Keeps Saying 'I Don't Know')\n"
    "Turn 1 (Stage 3):\n"
    "User: 'i want to tell them how i feel'\n"
    "Serena: 'That sounds like a good goal. What are you thinking of saying to them?'\n\n"
    
    "Turn 2 (Still Stage 3):\n"
    "User: 'i dont know yet'\n"
    "Serena: 'That's okay. What kind of approach feels right to you?'\n\n"
    
    "Turn 3 (SECOND 'I don't know' - Time to Act):\n"
    "User: 'no idea'\n"
    "BAD (Keeps looping): 'What feels like the hardest part for you right now?'\n"
    "GOOD (Offers help or exits): 'That's completely okay. Would it help if I shared what some people find useful in these situations, or would you rather think about it on your own?'\n"
    "[Gives them agency: accept help OR decline gracefully]\n\n"
    
    "Turn 4a (If they want help):\n"
    "User: 'yeah sure'\n"
    "Serena (MOVE TO STAGE 4): 'Some people find it helpful to start with something like \"I want to talk about something that's been on my mind.\" That way it's honest but not accusatory. What do you think?'\n\n"
    
    "Turn 4b (If they don't want help):\n"
    "User: 'nah im good'\n"
    "Serena (MOVE TO STAGE 5): 'Okay, sounds good. Take your time figuring it out. I'm here if you want to talk more later.'\n\n"
    
    "Turn 4c (If they give a THIRD 'I don't know'):\n"
    "User: 'nothing'\n"
    "Serena (MOVE TO STAGE 5 immediately): 'No worries. Sometimes it takes time to figure these things out. I'm here whenever you want to talk.'\n"
    "[Don't keep pushing - respect their boundary]\n\n"
    
    "EXAMPLE 5: How Context Should Accumulate (Preventing Repeated Questions)\n"
    "Turn 1:\n"
    "User: 'My friends are bullying me'\n"
    "Serena: 'That sounds really tough. What's been on your mind about it?'\n"
    "Context: 'User: friends bullying them.'\n\n"
    
    "Turn 2:\n"
    "User: 'I want to message them'\n"
    "Serena: 'Messaging them sounds like a thoughtful approach. What are you thinking of saying?'\n"
    "Context: 'User: friends bullying. Goal: message them.'\n"
    "[Note: ADDED 'Goal: message them' to previous context]\n\n"
    
    "Turn 3:\n"
    "User: 'i dont know yet'\n"
    "Serena: 'That's okay. What kind of message feels right to you?'\n"
    "Context: 'User: friends bullying. Goal: message. Asked approach 1x - unsure.'\n"
    "[Note: TRACKED that we asked once and they're unsure]\n\n"
    
    "Turn 4:\n"
    "User: 'no idea'\n"
    "Serena: 'That's completely okay. Would it help if I suggested a way to start?'\n"
    "Context: 'User: friends bullying. Goal: message. Asked approach 2x - unsure. Offered help.'\n"
    "[Note: Counted 2nd 'I don't know', so offered help instead of asking again]\n\n"
    
    "Turn 5 (if they decline):\n"
    "User: 'nah'\n"
    "Serena (STAGE 5): 'No worries. Take your time. I'm here when you're ready.'\n"
    "Context: 'User: friends bullying. Goal: message. Asked 2x - unsure. Offered help - declined. Wrapped up.'\n"
    "[Note: Logged everything so if they return, we don't repeat the same questions]\n\n"
    
    "KEY: The context field is a RUNNING LOG, not a snapshot. Each turn ADDS to previous notes.\n\n"
    
    "Key Philosophy:\n"
    "1. Your job is to SUPPORT, not SOLVE - help them think, don't think for them\n"
    "2. Surface-level acknowledgment is often more powerful than deep investigation\n"
    "3. Empowering questions > Information gathering questions\n"
    "4. Trust users to know their situation better than you ever will\n"
    "5. Sometimes people just need to feel heard - that's enough\n"
    "6. Being concise shows you respect their autonomy\n"
    "7. Move quickly from 'What happened?' to 'What do YOU think?'\n"
    "8. CRITICAL: If they say 'I don't know' twice, STOP asking questions - offer help or wrap up\n"
    "9. Respect 'I don't know' as a valid answer, not an invitation to keep probing\n\n"
    
    "Remember: You're a supportive mirror that helps users see their own thoughts more clearly, not a problem-solving consultant."
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

        # --- SESSION PARAMETER MANAGEMENT ---
        session_info = req.get("sessionInfo", {})
        session_params = session_info.get("parameters", {})
        
        # Track conversation turns within this session
        turn_count = session_params.get("turn_count", 0) + 1
        session_params["turn_count"] = turn_count
        logger.info(f"Turn count in this session: {turn_count}")
        
        # Retrieve conversation history from session (if available)
        conversation_history = session_params.get("conversation_history", [])
        logger.debug(f"Session conversation history: {len(conversation_history)} entries")
        
        # --- END SESSION PARAMETER MANAGEMENT ---

        user_profile = get_user_profile(user_id) or {}
        profile = user_profile.get("profile", {})

        # --- LOAD CONTEXT ---
        bot_context = profile.get("context", "")
        logger.debug(f"Loaded bot context: {bot_context}")
        # --- END LOAD CONTEXT ---

        # --- INSTRUCTION INJECTION ---
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
        logger.debug(f"User instructions: {formatted_instructions}")
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

        # --- LONG-TERM MEMORY RETRIEVAL ---
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
                logger.info(f"Found {len(retrieved)} relevant memories.")
            else:
                retrieved_text = "No relevant memories found."
        else:
            retrieved_text = "Memory retrieval is disabled for this user."
        # --- END LONG-TERM MEMORY RETRIEVAL ---

        # --- TIME CONTEXT & STAGE RESET LOGIC ---
        time_context = ""
        current_stage = profile.get("current_stage", "Stage 1: Getting to Know Each Other")
        logger.info(f"Stage loaded from profile: {current_stage}")
        
        try:
            last_seen_str = profile.get("updated_at")
            if last_seen_str:
                last_interaction_time = datetime.fromisoformat(last_seen_str)
                time_delta = datetime.now(timezone.utc) - last_interaction_time
                
                # If last interaction was over 24 hours ago, reset stage AND context
                if time_delta > timedelta(hours=24):
                    time_ago_str = format_time_delta(last_seen_str).strip('()')
                    time_context = f"Note: User's last interaction was {time_ago_str}. Acknowledge this pause and re-establish rapport."
                    current_stage = 'Stage 1: Getting to Know Each Other'
                    bot_context = ""  # <-- CLEAR CONTEXT
                    session_params["turn_count"] = 1
                    logger.info(f"User inactive for {time_delta}. Reset to Stage 1, cleared context, reset turn count.")
                # If over 15 mins but less than 24h, just add time context
                elif time_delta > timedelta(minutes=15):
                    time_ago_str = format_time_delta(last_seen_str).strip('()')
                    time_context = f"Note: User's last interaction was {time_ago_str}. Acknowledge this pause."
                    logger.info(f"Time context added: {time_ago_str}")

        except Exception as e:
            logger.warning(f"Could not analyze user profile timestamp: {e}")
        # --- END TIME CONTEXT & STAGE RESET LOGIC ---
        short_term_memory_summary = ""
        if conversation_history:
            # Include recent conversation context from this session
            recent_context = []
            for entry in conversation_history[-5:]:  # Last 3 exchanges
                turn_num = entry.get('turn', '?')
                user_msg = entry.get('user', 'No message')
                assistant_msg = entry.get('assistant', 'No response')
                
                # Format: Show both sides of the conversation
                recent_context.append(
                    f"Turn {turn_num}:\n"
                    f"  User: {user_msg}\n"
                    f"  You replied: {assistant_msg}"
                )
            
            short_term_memory_summary = "\n\n".join(recent_context) if recent_context else "Session just started"
        else:
            short_term_memory_summary = "Session just started - no prior context"

        logger.debug(f"Short-term session memory:\n{short_term_memory_summary}")
        # --- END SHORT-TERM MEMORY SUMMARY ---

        # --- BUILD SYSTEM INSTRUCTION ---
        system_instruction = SERENA_SYSTEM_PROMPT_TEMPLATE.format(
            formatted_instructions=formatted_instructions,
            current_stage=current_stage
        )
        # --- END BUILD SYSTEM INSTRUCTION ---

        # --- BUILD USER PROMPT ---
        prompt = (
            "# --- CONTEXT FOR THIS RESPONSE ---\n\n"
            f"[Your Context Notes]\n{bot_context if bot_context else 'No notes yet - this is a fresh start'}\n\n"
            f"[Time Context]\n{time_context if time_context else 'Ongoing conversation'}\n\n"
            f"[Current Stage]\n{current_stage}\n\n"
            f"[Turn Count in This Session]\n{turn_count}\n\n"
            f"[Short-Term Session Context]\n{short_term_memory_summary}\n\n"
            f"[Long-Term Memories]\n{retrieved_text}\n\n"
            f"--- END CONTEXT ---\n\n"
            f"User: {user_text}\n\n"
            "**Provide your JSON response (with reply_text, new_stage, AND context):**"
        )
        logger.debug(f"Prompt context built. Turn: {turn_count}, Stage: {current_stage}")
        # --- END BUILD USER PROMPT ---

        logger.info("Generating response...")
        raw_response_text = generate_text(
            prompt, 
            system_instruction=system_instruction, 
            max_output_tokens=2500, 
            temperature=0.7
        ).strip()

        # --- PARSE JSON RESPONSE ---
        # The bot receives old context in the prompt and is responsible for 
        # maintaining cumulative notes. Code just replaces with bot's output.

        logger.debug(f"Raw response: {raw_response_text[:200]}...")
        parse_failed = False
        reply_text = "I'm having a little trouble thinking right now. Could you try that again?"
        new_stage = current_stage
        # Default to the OLD context as a safety net
        new_context = bot_context  

        try:
            json_match = re.search(r'\{.*\}', raw_response_text, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group(0))
                reply_text = response_json.get("reply_text", reply_text)
                new_stage = response_json.get("new_stage", current_stage)
                
                # If the bot provides a context, use it.
                # If it FORGETS the context key, default to the old one.
                new_context = response_json.get("context", bot_context) 
                
                logger.info(f"Parsed successfully. New stage: {new_stage}")
                logger.debug(f"Context from bot: {new_context[:100]}...")
            else:
                parse_failed = True
                logger.error("No JSON found in response.")
                # If parsing fails, new_context is already set to bot_context
                reply_text = raw_response_text
                
        except json.JSONDecodeError as e:
            parse_failed = True
            logger.error(f"Failed to parse JSON: {e}")
            # If parsing fails, new_context is already set to bot_context
        # --- END PARSE JSON RESPONSE ---

        # --- UPDATE SESSION PARAMETERS ---
        
        # ONLY save to history if the parse was successful
        if not parse_failed:
            new_history_entry = {
                "turn": turn_count,
                "user": user_text[:200],
                "assistant": reply_text[:200],
                "stage": new_stage,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            conversation_history.append(new_history_entry)
            
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]
            
            logger.info(f"Updated session history. Size: {len(conversation_history)}")
        else:
            # If parse failed, do NOT save this turn to history
            logger.warning("Parse failed. Not saving this turn to session history.")

        session_params["conversation_history"] = conversation_history
        # --- END UPDATE SESSION PARAMETERS ---

        # --- PREPARE PROFILE UPDATE ---
        profile_update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "current_stage": new_stage,
            "context": new_context  # <-- ADD THIS
        }

        # Special case: If moving to Stage 1, clear context
        if new_stage == "Stage 1: Getting to Know Each Other" and current_stage != "Stage 1: Getting to Know Each Other":
            profile_update_data["context"] = ""
            logger.info("Stage changed to 1 - clearing context for fresh start")
        # --- END PREPARE PROFILE UPDATE ---

        # --- MEMORY & INSTRUCTION SAVING (With Consent) ---
        if has_consent:
            logger.info("Analyzing exchange for memory and instructions...")
            analysis_result = summarize_conversation(user_text, reply_text)
            
            new_instruction = analysis_result.get("instruction")
            if new_instruction and new_instruction not in user_instructions_list:
                logger.info(f"Adding new instruction: {new_instruction}")
                user_instructions_list.append(new_instruction)
                profile_update_data['user_instructions'] = user_instructions_list

            if analysis_result.get("is_significant"):
                summary = analysis_result.get("summary")
                if summary != "No summary generated.":
                    if save_memory(user_id, summary, {
                        "topic": "conversation_exchange",
                        "session_id": session_id,
                        "stage": new_stage,
                        "turn": turn_count
                    }):
                        logger.info("Memory saved successfully.")
                    else:
                        logger.error("Failed to save memory.")
        # --- END MEMORY & INSTRUCTION SAVING ---

        # --- SAVE PROFILE UPDATE ---
        try:
            profile.update(profile_update_data)
            upsert_user_profile(user_id, profile)
            logger.info(f"Profile updated for {user_id}.")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
        # --- END SAVE PROFILE UPDATE ---

        # --- BUILD RESPONSE WITH SESSION PARAMETERS ---
        response = {
            "fulfillment_response": {
                "messages": [{"text": {"text": [reply_text]}}]
            },
            "session_info": {
                "parameters": session_params  # Return updated session params
            }
        }
        logger.info("Response completed successfully")
        # --- END BUILD RESPONSE ---
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in dialogflow_webhook: {e}")
        logger.error(traceback.format_exc())
        error_response = {
            "fulfillment_response": {
                "messages": [{"text": {"text": ["I'm having trouble right now. Please try again in a moment."]}}]
            }
        }
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
            'current_stage': "Stage 1: Getting to Know Each Other",
            'context': "",  # <-- ADD THIS
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