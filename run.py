import uvicorn
import sys
import os

# Add the current directory to sys.path so modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Email Triage Assistant API Server...")
    print("📍 API Docs: http://localhost:8000/docs")
    print("🌐 Dashboard: http://localhost:8000")
    print("👉 Login Page: http://localhost:8000")
    print("\nPress CTRL+C to stop the server\n")
    
    # Run the application using the import string
    # This relies on the 'src' package being importable from the current directory
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)
