"""Mock email data generator for development and testing"""

import random
from datetime import datetime, timedelta
from typing import List
from faker import Faker

from ..models import Email, EmailAddress, EmailThread, EmailCategory


class MockEmailGenerator:
    """Generate realistic mock email data"""
    
    def __init__(self, seed: int = 42):
        self.faker = Faker()
        Faker.seed(seed)
        random.seed(seed)
        
        # Pre-defined realistic email templates
        self.work_subjects = [
            "Q4 Project Status Update",
            "Meeting Request: Product Roadmap Discussion",
            "URGENT: Server Issues in Production",
            "Code Review: PR #1234",
            "Team Sync - Weekly Planning",
            "Budget Approval Needed",
            "Client Feedback on Latest Release",
            "Performance Review Schedule",
            "Security Audit Results",
            "API Integration Questions"
        ]
        
        self.personal_subjects = [
            "Dinner plans this weekend?",
            "Happy Birthday!",
            "Vacation photos",
            "Quick question about the party",
            "Thanks for your help!",
            "Catching up",
            "Movie recommendations?",
            "Family reunion details"
        ]
        
        self.newsletter_subjects = [
            "Weekly Tech Newsletter - Issue #127",
            "Your Monthly Summary",
            "Top Stories This Week",
            "New Articles You Might Like",
            "Developer Updates - February 2026"
        ]
        
        self.promotional_subjects = [
            "50% OFF - Limited Time Offer!",
            "Exclusive Deal Just For You",
            "New Arrivals - Check Them Out",
            "Flash Sale Ends Tonight",
            "Your Personalized Recommendations"
        ]
    
    def generate_email(self, category: EmailCategory = None) -> Email:
        """Generate a single mock email"""
        
        if not category:
            category = random.choice(list(EmailCategory))
        
        # Generate email ID and thread ID
        email_id = self.faker.uuid4()
        thread_id = self.faker.uuid4()
        
        # Select subject based on category
        if category == EmailCategory.WORK:
            subject = random.choice(self.work_subjects)
        elif category == EmailCategory.PERSONAL:
            subject = random.choice(self.personal_subjects)
        elif category == EmailCategory.NEWSLETTER:
            subject = random.choice(self.newsletter_subjects)
        elif category == EmailCategory.PROMOTIONAL:
            subject = random.choice(self.promotional_subjects)
        else:
            subject = self.faker.sentence(nb_words=6)
        
        # Generate sender and recipients
        sender = EmailAddress(
            email=self.faker.email(),
            name=self.faker.name()
        )
        
        recipients = [
            EmailAddress(
                email=self.faker.email(),
                name=self.faker.name()
            )
        ]
        
        # Generate body text
        body_text = self._generate_email_body(category)
        
        # Generate received time (within last 30 days)
        received_at = datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        email = Email(
            id=email_id,
            thread_id=thread_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            body_text=body_text,
            received_at=received_at,
            category=category
        )
        
        return email
    
    def generate_batch(self, count: int = 100, 
                      category_distribution: dict = None) -> List[Email]:
        """
        Generate a batch of emails with specified distribution
        
        Args:
            count: Number of emails to generate
            category_distribution: Dict mapping category to percentage
                                  e.g., {EmailCategory.WORK: 0.4, ...}
        """
        if not category_distribution:
            # Default distribution
            category_distribution = {
                EmailCategory.WORK: 0.35,
                EmailCategory.PERSONAL: 0.15,
                EmailCategory.NEWSLETTER: 0.25,
                EmailCategory.PROMOTIONAL: 0.15,
                EmailCategory.URGENT: 0.05,
                EmailCategory.SOCIAL: 0.05
            }
        
        emails = []
        for _ in range(count):
            # Select category based on distribution
            rand = random.random()
            cumulative = 0
            selected_category = EmailCategory.WORK
            
            for category, percentage in category_distribution.items():
                cumulative += percentage
                if rand <= cumulative:
                    selected_category = category
                    break
            
            email = self.generate_email(selected_category)
            emails.append(email)
        
        return emails
    
    def generate_thread(self, message_count: int = 50, 
                       category: EmailCategory = EmailCategory.WORK) -> EmailThread:
        """Generate a mock email thread with specified message count"""
        
        thread_id = self.faker.uuid4()
        subject = random.choice(self.work_subjects)
        
        # Generate participants (3-5 people)
        participants = [
            EmailAddress(email=self.faker.email(), name=self.faker.name())
            for _ in range(random.randint(3, 5))
        ]
        
        messages = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(message_count):
            sender = random.choice(participants)
            recipients = [p for p in participants if p.email != sender.email]
            
            # Add time variation (2-8 hours between messages)
            time_offset = timedelta(hours=random.randint(2, 8) * i)
            
            email = Email(
                id=self.faker.uuid4(),
                thread_id=thread_id,
                subject=f"Re: {subject}" if i > 0 else subject,
                sender=sender,
                recipients=recipients,
                body_text=self._generate_email_body(category),
                received_at=base_time + time_offset,
                in_reply_to=messages[-1].id if messages else None,
                category=category
            )
            messages.append(email)
        
        thread = EmailThread(
            thread_id=thread_id,
            subject=subject,
            participants=participants,
            messages=messages
        )
        
        return thread
    
    def _generate_email_body(self, category: EmailCategory) -> str:
        """Generate realistic email content based on category"""
        
        if category == EmailCategory.WORK:
            templates = [
                f"Hi team,\n\n{self.faker.paragraph(nb_sentences=5)}\n\nCould you please review and provide feedback by end of day?\n\nBest regards,",
                f"Hello,\n\n{self.faker.paragraph(nb_sentences=3)}\n\nLet me know if you have any questions.\n\nThanks,",
                f"Quick update:\n\n{self.faker.paragraph(nb_sentences=4)}\n\nNext steps:\n- {self.faker.sentence()}\n- {self.faker.sentence()}\n\nPlease confirm.",
            ]
        elif category == EmailCategory.PERSONAL:
            templates = [
                f"Hey!\n\n{self.faker.paragraph(nb_sentences=3)}\n\nLet me know what you think!\n\nCheers,",
                f"Hi there,\n\n{self.faker.paragraph(nb_sentences=2)}\n\nTalk soon!",
                f"{self.faker.paragraph(nb_sentences=4)}\n\nTake care!"
            ]
        elif category == EmailCategory.NEWSLETTER:
            templates = [
                f"# Top Stories This Week\n\n{self.faker.paragraph(nb_sentences=6)}\n\n## Featured Article\n{self.faker.paragraph(nb_sentences=4)}\n\nUnsubscribe | Manage Preferences",
                f"Your weekly digest:\n\n{self.faker.paragraph(nb_sentences=8)}\n\nRead more on our website\n\nTo unsubscribe, click here."
            ]
        elif category == EmailCategory.PROMOTIONAL:
            templates = [
                f"🎉 SPECIAL OFFER INSIDE! 🎉\n\n{self.faker.paragraph(nb_sentences=3)}\n\nUse code: SAVE50\n\nShop now: [link]\n\nUnsubscribe",
                f"Don't miss out on this amazing deal!\n\n{self.faker.paragraph(nb_sentences=4)}\n\nLimited time only!\n\nUnsubscribe from promotional emails."
            ]
        elif category == EmailCategory.URGENT:
            templates = [
                f"URGENT: {self.faker.sentence()}\n\n{self.faker.paragraph(nb_sentences=3)}\n\nPlease address this ASAP.\n\nThanks,",
                f"IMMEDIATE ACTION REQUIRED\n\n{self.faker.paragraph(nb_sentences=2)}\n\nDeadline: Today EOD\n\nPlease confirm receipt."
            ]
        else:
            templates = [f"{self.faker.paragraph(nb_sentences=5)}"]
        
        return random.choice(templates)
    
    def generate_realistic_inbox(self, total_emails: int = 200) -> dict:
        """
        Generate a realistic inbox with varied email types
        
        Returns:
            dict with 'emails' and 'threads'
        """
        # Generate individual emails
        emails = self.generate_batch(total_emails)
        
        # Generate a few long threads
        threads = []
        for i in range(5):
            thread_length = random.randint(30, 70)
            thread = self.generate_thread(
                message_count=thread_length,
                category=random.choice([EmailCategory.WORK, EmailCategory.URGENT])
            )
            threads.append(thread)
        
        return {
            'emails': emails,
            'threads': threads,
            'summary': {
                'total_emails': total_emails,
                'total_threads': len(threads),
                'total_messages_in_threads': sum(t.message_count for t in threads)
            }
        }
