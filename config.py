import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure Configuration
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")

# App Configuration
PORT = int(os.getenv("PORT", 6003))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging Setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("azure-agent")

def validate_config():
    """Validate that all required environment variables are set."""
    missing = []
    if not AZURE_TENANT_ID: missing.append("AZURE_TENANT_ID")
    if not AZURE_CLIENT_ID: missing.append("AZURE_CLIENT_ID")
    if not AZURE_CLIENT_SECRET: missing.append("AZURE_CLIENT_SECRET")
    if not AZURE_SUBSCRIPTION_ID: missing.append("AZURE_SUBSCRIPTION_ID")
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    return True
