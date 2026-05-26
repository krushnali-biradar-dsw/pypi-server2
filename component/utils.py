"""
Security and helper utilities for A2A and ML Agent Systems.
"""

import os
import sys
import logging
import hashlib
from datetime import datetime

# Configure logging with premium styling
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("A2ASecureAgent.Utils")

def get_hash(data: str) -> str:
    """Generate SHA-256 hash of a string for secure integrity checks."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def secure_log(message: str, level: str = "INFO"):
    """Secure logging wrapper that censors common API keys and patterns."""
    censored = message
    # Simple censorship for demo purposes
    for pattern in ["sk-", "api_key", "password", "secret"]:
        if pattern in censored.lower():
            censored = "[REDACTED SECURITY SENSITIVE DATA]"
            break
            
    if level.upper() == "INFO":
        logger.info(censored)
    elif level.upper() == "WARNING":
        logger.warning(censored)
    elif level.upper() == "ERROR":
        logger.error(censored)
    else:
        logger.debug(censored)

def check_environment() -> dict:
    """Verifies that key security variables are set."""
    status = {
        "AIR_GAPPED": os.environ.get("AIR_GAPPED", "false").lower() == "true",
        "TIMESTAMP": datetime.utcnow().isoformat() + "Z"
    }
    secure_log(f"Environment check completed: Air-Gapped Mode = {status['AIR_GAPPED']}")
    return status
