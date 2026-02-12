"""Start the Email Triage Assistant API server"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Email Triage Assistant API Server...")
    print("📍 API Docs: http://localhost:8000/docs")
    print("🌐 Dashboard: http://localhost:8000")
    print("\nPress CTRL+C to stop the server\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
