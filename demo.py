"""Demo script to test Email Triage Assistant functionality"""

from src.models import Email, EmailAddress, EmailThread, EmailCategory
from src.ingestion import MockEmailGenerator
from src.triage import TriageAgent, RuleBasedClassifier
from src.priority import PriorityScorer
from src.compression import EmailThreadCompressor

def main():
    print("=" * 80)
    print("Email Triage Assistant - Demo Script")
    print("=" * 80)
    print()
    
    # Initialize components
    print("📦 Initializing components...")
    generator = MockEmailGenerator()
    triage = TriageAgent()
    scorer = PriorityScorer()
    compressor = EmailThreadCompressor()
    print("✓ Components initialized\n")
    
    # Generate mock emails
    print("📧 Generating 10 mock emails...")
    emails = generator.generate_batch(10)
    print(f"✓ Generated {len(emails)} emails\n")
    
    # Process emails
    print("🔍 Processing emails (Triage + Priority Scoring)...")
    for i, email in enumerate(emails, 1):
        # Triage
        email = triage.classify_email(email)
        
        # Priority scoring
        email.priority_score = scorer.calculate_priority(email)
        email.priority_level = scorer.assign_priority_level(email.priority_score)
        
        print(f"  {i}. [{email.category.value.upper():12}] {email.subject[:45]:45} | Priority: {email.priority_score:5.2f} ({email.priority_level.name})")
    
    print(f"\n✓ Processed {len(emails)} emails\n")
    
    # Generate and compress a long thread
    print("🧵 Generating email thread with 50 messages...")
    thread = generator.generate_thread(message_count=50)
    print(f"✓ Generated thread: '{thread.subject}' with {thread.message_count} messages\n")
    
    # Compress thread
    print("🗜️  Compressing thread using ScaleDown algorithm...")
    thread = compressor.compress_thread(thread)
    stats = compressor.get_compression_stats(thread)
    
    print(f"✓ Compression complete!")
    print(f"  - Original tokens: {stats['original_tokens']:,}")
    print(f"  - Compressed tokens: {stats['compressed_tokens']:,}")
    print(f"  - Compression ratio: {stats['compression_ratio_pct']:.1f}%")
    print(f"  - Tokens saved: {stats['tokens_saved']:,}")
    print(f"  - Decisions extracted: {stats['decisions_extracted']}")
    print(f"  - Questions identified: {stats['questions_identified']}")
    print(f"  - Action items: {stats['action_items_count']}")
    print()
    
    # Display compressed summary
    print("📋 Compressed Thread Summary:")
    print("-" * 80)
    print(thread.compressed_summary[:500] if thread.compressed_summary else "No summary")
    if thread.compressed_summary and len(thread.compressed_summary) > 500:
        print(f"\n... (truncated, full summary is {len(thread.compressed_summary)} characters)")
    print("-" * 80)
    print()
    
    # Category distribution
    print("📊 Category Distribution:")
    categories = {}
    for email in emails:
        cat = email.category.value if email.category else 'unknown'
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(emails)) * 100
        bar = "█" * int(percentage / 5)
        print(f"  {cat:12} | {bar:20} {count:2} ({percentage:5.1f}%)")
    print()
    
    # Priority distribution
    print("⭐ Priority Distribution:")
    priorities = {}
    for email in emails:
        pri = email.priority_level.name if email.priority_level else 'UNASSIGNED'
        priorities[pri] = priorities.get(pri, 0) + 1
    
    for pri, count in sorted(priorities.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(emails)) * 100
        bar = "█" * int(percentage / 5)
        print(f"  {pri:10} | {bar:20} {count:2} ({percentage:5.1f}%)")
    print()
    
    print("=" * 80)
    print("✓ Demo Complete!")
    print()
    print("Next steps:")
    print("  1. Start the API server: python run_server.py")
    print("  2. Visit http://localhost:8000 for the dashboard")
    print("  3. Visit http://localhost:8000/docs for API documentation")
    print("=" * 80)

if __name__ == "__main__":
    main()
