"""
Encryption module for GenAI Chatbot using Google Cloud KMS.
Handles encryption/decryption of sensitive conversation data.

IMPORTANT: Add to requirements.txt:
    google-cloud-kms==2.20.0
"""

import os
import base64
import logging
from google.cloud import kms
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "genai-bot-kdf")
LOCATION = os.environ.get("REGION", "asia-south1")
KEY_RING = "chatbot-encryption"
KEY_NAME = "memory-encryption-key"


class EncryptionService:
    """Handles encryption/decryption using Google Cloud KMS"""
    
    def __init__(self):
        """Initialize KMS client and construct key path"""
        try:
            self.client = kms.KeyManagementServiceClient()
            self.key_path = self.client.crypto_key_path(
                PROJECT_ID, LOCATION, KEY_RING, KEY_NAME
            )
            logger.info(f"Encryption service initialized with key: {self.key_path}")
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt plaintext string using Cloud KMS.
        
        Args:
            plaintext: The text to encrypt
            
        Returns:
            Base64-encoded encrypted string, or None if encryption fails
        """
        if not plaintext:
            return None
            
        try:
            # Convert string to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Encrypt using KMS
            encrypt_response = self.client.encrypt(
                request={
                    "name": self.key_path,
                    "plaintext": plaintext_bytes
                }
            )
            
            # Convert encrypted bytes to base64 for storage
            encrypted_b64 = base64.b64encode(encrypt_response.ciphertext).decode('utf-8')
            logger.debug(f"Successfully encrypted {len(plaintext)} characters")
            
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, encrypted_b64: str) -> Optional[str]:
        """
        Decrypt base64-encoded ciphertext using Cloud KMS.
        
        Args:
            encrypted_b64: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string, or None if decryption fails
        """
        if not encrypted_b64:
            return None
            
        try:
            # Convert base64 to bytes
            ciphertext_bytes = base64.b64decode(encrypted_b64)
            
            # Decrypt using KMS
            decrypt_response = self.client.decrypt(
                request={
                    "name": self.key_path,
                    "ciphertext": ciphertext_bytes
                }
            )
            
            # Convert decrypted bytes back to string
            plaintext = decrypt_response.plaintext.decode('utf-8')
            logger.debug(f"Successfully decrypted to {len(plaintext)} characters")
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_dict(self, data: dict, fields_to_encrypt: list) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dictionary with specified fields encrypted
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_value = self.encrypt(str(encrypted_data[field]))
                if encrypted_value:
                    encrypted_data[field] = encrypted_value
                    encrypted_data[f"{field}_encrypted"] = True
                else:
                    logger.warning(f"Failed to encrypt field: {field}")
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields_to_decrypt: list) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dictionary with specified fields decrypted
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            # Check if field is marked as encrypted
            if decrypted_data.get(f"{field}_encrypted"):
                encrypted_value = decrypted_data.get(field)
                if encrypted_value:
                    decrypted_value = self.decrypt(encrypted_value)
                    if decrypted_value:
                        decrypted_data[field] = decrypted_value
                        # Remove encryption flag
                        decrypted_data.pop(f"{field}_encrypted", None)
                    else:
                        logger.warning(f"Failed to decrypt field: {field}")
        
        return decrypted_data


# Global instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get or create global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service