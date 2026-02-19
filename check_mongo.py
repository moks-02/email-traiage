
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.errors import ConnectionFailure, DuplicateKeyError
    print("MongoDB drivers installed successfully.")
except ImportError:
    print("MongoDB drivers are MISSING. Please install 'motor'.")
