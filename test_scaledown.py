"""
Test script for ScaleDown AI API integration
Demonstrates how to use the API with the Email Triage Assistant
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.api.scaledown_integration import ScaleDownAPIClient, HybridCompressor
from src.ingestion import MockEmailGenerator
from src.compression import EmailThreadCompressor


def print_separator(title):
    """Print a formatted section separator"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_configuration():
    """Test 1: Check configuration"""
    print_separator("TEST 1: Configuration Check")
    
    print(f"ScaleDown API Key: {'✅ Configured' if Config.is_scaledown_configured() else '❌ Not configured'}")
    print(f"Base URL: {Config.SCALEDOWN_BASE_URL}")
    print(f"Compression enabled: {Config.USE_SCALEDOWN_FOR_COMPRESSION}")
    print(f"Classification enabled: {Config.USE_SCALEDOWN_FOR_CLASSIFICATION}")
    print(f"Responses enabled: {Config.USE_SCALEDOWN_FOR_RESPONSES}")
    
    if not Config.is_scaledown_configured():
        print("\n⚠️  ScaleDown AI not configured!")
        print("To configure:")
        print("1. Copy config.example.py to config.py")
        print("2. Add your API key: SCALEDOWN_API_KEY = 'sk-your-key-here'")
        print("3. Adjust SCALEDOWN_BASE_URL if needed")
        print("\nOr set environment variable: SCALEDOWN_API_KEY=sk-your-key-here")
        return False
    
    return True


def test_api_health():
    """Test 2: Check API health"""
    print_separator("TEST 2: API Health Check")
    
    if not Config.is_scaledown_configured():
        print("⏭️  Skipping (API not configured)")
        return False
    
    client = ScaleDownAPIClient(
        api_key=Config.SCALEDOWN_API_KEY,
        base_url=Config.SCALEDOWN_BASE_URL
    )
    
    print("Checking API health...")
    is_healthy = client.health_check()
    
    if is_healthy:
        print("✅ API is healthy and responding")
        return True
    else:
        print("❌ API is not responding")
        print("   - Check your API key")
        print("   - Verify the base URL")
        print("   - Check your internet connection")
        return False


def test_thread_compression():
    """Test 3: Thread compression with hybrid mode"""
    print_separator("TEST 3: Thread Compression (Hybrid Mode)")
    
    # Generate test thread
    print("Generating test email thread...")
    generator = MockEmailGenerator()
    thread = generator.generate_thread(
        message_count=20
    )
    
    print(f"Generated thread with {thread.message_count} messages")
    print(f"Participants: {len(thread.participants)}")
    
    # Initialize hybrid compressor
    client = None
    if Config.is_scaledown_configured():
        client = ScaleDownAPIClient(
            api_key=Config.SCALEDOWN_API_KEY,
            base_url=Config.SCALEDOWN_BASE_URL
        )
    
    local_compressor = EmailThreadCompressor()
    hybrid_compressor = HybridCompressor(
        api_client=client,
        local_compressor=local_compressor
    )
    
    # Compress
    print("\nCompressing thread...")
    compressed = hybrid_compressor.compress_thread(thread)
    
    # Results
    print(f"\n📊 Compression Results:")
    print(f"   Original tokens: {compressed.original_token_count:,}")
    print(f"   Compressed tokens: {compressed.compressed_token_count:,}")
    print(f"   Compression ratio: {compressed.compression_ratio:.1f}%")
    print(f"   Decisions extracted: {len(compressed.key_decisions)}")
    print(f"   Questions found: {len(compressed.unresolved_questions)}")
    print(f"   Action items: {sum(len(items) for items in compressed.action_items_by_person.values())}")
    
    if compressed.compressed_summary:
        print(f"\n📝 Summary preview:")
        print(f"   {compressed.compressed_summary[:200]}...")


def test_email_features():
    """Test 4: Individual email features"""
    print_separator("TEST 4: Email Classification & Analysis")
    
    if not Config.is_scaledown_configured():
        print("⏭️  Skipping (API not configured)")
        return
    
    client = ScaleDownAPIClient(
        api_key=Config.SCALEDOWN_API_KEY,
        base_url=Config.SCALEDOWN_BASE_URL
    )
    
    # Generate test email
    generator = MockEmailGenerator()
    emails = generator.generate_batch(count=1)
    test_email = emails[0]
    
    print(f"Testing with email:")
    print(f"   From: {test_email.sender.email}")
    print(f"   Subject: {test_email.subject}")
    print(f"   Body preview: {test_email.body_text[:100]}...")
    
    # Test classification
    print("\n🏷️  Testing classification...")
    try:
        result = client.classify_email(test_email)
        if result.get('fallback'):
            print("   ⚠️  API not available, would use local classification")
        else:
            print(f"   Category: {result.get('category', 'Unknown')}")
            print(f"   Confidence: {result.get('confidence', 0):.2%}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test entity extraction
    print("\n🔍 Testing entity extraction...")
    try:
        entities = client.extract_entities(test_email.body_text)
        if entities:
            print(f"   Found {len(entities)} entities:")
            for entity in entities[:5]:
                print(f"      - {entity}")
        else:
            print("   ⚠️  No entities extracted (API may not be available)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test sentiment analysis
    print("\n😊 Testing sentiment analysis...")
    try:
        sentiment = client.analyze_sentiment(test_email.body_text)
        if sentiment.get('error'):
            print(f"   ⚠️  API error: {sentiment['error']}")
        else:
            print(f"   Sentiment: {sentiment.get('sentiment', 'unknown')}")
            print(f"   Score: {sentiment.get('score', 0):.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_batch_processing():
    """Test 5: Batch processing"""
    print_separator("TEST 5: Batch Processing")
    
    if not Config.is_scaledown_configured():
        print("⏭️  Skipping (API not configured)")
        return
    
    client = ScaleDownAPIClient(
        api_key=Config.SCALEDOWN_API_KEY,
        base_url=Config.SCALEDOWN_BASE_URL
    )
    
    # Generate batch of emails
    print("Generating batch of 10 test emails...")
    generator = MockEmailGenerator()
    emails = generator.generate_batch(count=10)
    
    print(f"Generated {len(emails)} emails")
    
    # Batch process
    print("\n📦 Processing batch...")
    try:
        results = client.batch_process(emails)
        if results:
            print(f"   ✅ Successfully processed {len(results)} emails")
            if results[0]:
                print(f"   Sample result: {results[0]}")
        else:
            print("   ⚠️  API returned empty results (may not be available)")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║          ScaleDown AI Integration Test Suite                     ║")
    print("║          Email Triage Assistant v1.0                             ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    
    # Run tests
    configured = test_configuration()
    
    if configured:
        healthy = test_api_health()
        if not healthy:
            print("\n⚠️  API health check failed. Tests will demonstrate fallback behavior.")
    
    test_thread_compression()  # Works with or without API
    test_email_features()
    test_batch_processing()
    
    # Final summary
    print_separator("Test Summary")
    
    if Config.is_scaledown_configured():
        print("✅ ScaleDown AI is configured")
        print("\nYour system will:")
        print("   1. Try to use ScaleDown AI API for enhanced features")
        print("   2. Fall back to local processing if API is unavailable")
        print("   3. Provide consistent results regardless of API status")
        
        print("\n🚀 Next Steps:")
        print("   1. Start the API server: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        print("   2. Check API status: http://localhost:8000/api/scaledown/status")
        print("   3. Use the dashboard: http://localhost:8000")
        print("   4. View API docs: http://localhost:8000/docs")
    else:
        print("⚠️  ScaleDown AI is NOT configured")
        print("\nYour system will:")
        print("   1. Use local processing for all features")
        print("   2. Work normally without API access")
        print("   3. Be ready to use API once configured")
        
        print("\n📝 To enable ScaleDown AI:")
        print("   1. Copy config.example.py to config.py")
        print("   2. Add your API key to config.py")
        print("   3. Run this test again")
    
    print("\n")


if __name__ == "__main__":
    main()
