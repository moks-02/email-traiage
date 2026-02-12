# ScaleDown AI API Configuration

# Copy this file to config.py and fill in your details
# DO NOT commit config.py to version control

# Your ScaleDown AI API Configuration
SCALEDOWN_API_KEY = "mKipJXLcwB7k0rOpDuMvO9RLWzPEjbmB7lfchRCS"
SCALEDOWN_BASE_URL = "https://api.scaledown.ai/v1"  # or your custom endpoint

# API Settings
SCALEDOWN_TIMEOUT = 30  # seconds
SCALEDOWN_USE_BATCH = True  # Use batch processing when possible
SCALEDOWN_FALLBACK_TO_LOCAL = True  # Fall back to local processing if API fails

# Feature Flags
USE_SCALEDOWN_FOR_COMPRESSION = True
USE_SCALEDOWN_FOR_CLASSIFICATION = True
USE_SCALEDOWN_FOR_RESPONSES = True
USE_SCALEDOWN_FOR_ENTITIES = True

# Optional: OpenAI API (if you want to use both)
OPENAI_API_KEY = ""  # Leave empty if not using
