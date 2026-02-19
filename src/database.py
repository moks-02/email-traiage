
import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# Default to local MongoDB if not set
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "email_triage_db"

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            print(f"✅ Connected to MongoDB at {MONGO_URL}")
        except Exception as e:
            print(f"❌ Could not connect to MongoDB: {e}")

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")

    def get_emails_collection(self):
        return self.db.emails

    def get_threads_collection(self):
        return self.db.threads

    def get_tokens_collection(self):
        """Collection for storing OAuth tokens (one doc per provider per user)."""
        return self.db.oauth_tokens

# Singleton instance
db = Database()
