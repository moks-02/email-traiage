"""
Quick Setup Script for ScaleDown AI Integration
"""

import os
import sys

def main():
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║     ScaleDown AI Integration Setup                               ║")
    print("║     Email Triage Assistant                                       ║")
    print("╚═══════════════════════════════════════════════════════════════════╝\n")
    
    # Check if config.py exists
    config_exists = os.path.exists('config.py')
    
    if config_exists:
        print("✅ config.py found")
        
        # Try to read config
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.config import Config
            
            if Config.is_scaledown_configured():
                print("✅ ScaleDown AI API key configured")
                print(f"   Base URL: {Config.SCALEDOWN_BASE_URL}")
                print("\n🎉 You're all set! Your API is ready to use.")
            else:
                print("⚠️  config.py exists but API key not set")
                print("\n📝 Next steps:")
                print("   1. Open config.py")
                print("   2. Replace 'your-api-key-here' with your actual API key")
                print("   3. Run this setup script again")
        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print("📝 config.py not found - creating from template...")
        
        # Create config.py from example
        if os.path.exists('config.example.py'):
            with open('config.example.py', 'r') as f:
                content = f.read()
            
            with open('config.py', 'w') as f:
                f.write(content)
            
            print("✅ config.py created")
            print("\n📝 Next steps:")
            print("   1. Open config.py in your editor")
            print("   2. Find: SCALEDOWN_API_KEY = \"your-api-key-here\"")
            print("   3. Replace with: SCALEDOWN_API_KEY = \"mKipJXLcwB7k0rOpDuMvO9RLWzPEjbmB7lfchRCS\"")
            print("   4. Save the file")
            print("   5. Run this setup script again")
        else:
            print("❌ config.example.py not found")
            print("   Please ensure you're in the project root directory")
            return
    
    # Check .gitignore
    print("\n🔒 Security check...")
    gitignore_path = '.gitignore'
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
        
        if 'config.py' in gitignore_content:
            print("✅ config.py is in .gitignore (API key protected)")
        else:
            print("⚠️  Adding config.py to .gitignore...")
            with open(gitignore_path, 'a') as f:
                f.write('\n# API configuration (contains secrets)\nconfig.py\n')
            print("✅ config.py added to .gitignore")
    else:
        print("📝 Creating .gitignore...")
        with open(gitignore_path, 'w') as f:
            f.write('# Python\n__pycache__/\n*.py[cod]\n*$py.class\n\n')
            f.write('# Virtual Environment\nvenv/\nenv/\n\n')
            f.write('# API configuration (contains secrets)\nconfig.py\n\n')
            f.write('# IDE\n.vscode/\n.idea/\n')
        print("✅ .gitignore created")
    
    # Installation check
    print("\n📦 Checking dependencies...")
    try:
        import fastapi
        import uvicorn
        import requests
        import faker
        from dateutil import parser as dateparser
        print("✅ All required packages installed")
    except ImportError as e:
        print(f"⚠️  Missing package: {e.name}")
        print("\n📝 Install dependencies:")
        print("   pip install -r requirements.txt")
        return
    
    # Final instructions
    print("\n" + "="*70)
    print("Setup Complete! What to do next:")
    print("="*70)
    
    if config_exists:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from src.config import Config
            if Config.is_scaledown_configured():
                print("\n✅ Ready to use!")
                print("\n🧪 Test your integration:")
                print("   python test_scaledown.py")
                print("\n🚀 Start the server:")
                print("   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
                print("\n🌐 Access the dashboard:")
                print("   http://localhost:8000")
                print("\n📚 Check API docs:")
                print("   http://localhost:8000/docs")
                print("\n🔍 Check ScaleDown AI status:")
                print("   http://localhost:8000/api/scaledown/status")
            else:
                print("\n⚠️  Configure your API key first!")
                print("   1. Edit config.py")
                print("   2. Add your ScaleDown AI API key")
                print("   3. Run: python setup_scaledown.py")
        except:
            pass
    else:
        print("\n📝 Configure your API key:")
        print("   1. Edit config.py")
        print("   2. Add your ScaleDown AI API key")
        print("   3. Run: python setup_scaledown.py")
    
    print("\n📖 For detailed instructions, see:")
    print("   SCALEDOWN_SETUP.md")
    print("\n")


if __name__ == "__main__":
    main()
