from dotenv import load_dotenv
import os
from pymongo import MongoClient

# Load MongoDB URI from environment variable
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Initialize MongoDB client
if MONGO_URI:
    client = MongoClient(MONGO_URI)
    db = client.get_database('anything2image1')
else:
    raise ValueError("MONGO_URI environment variable is not set. Please set it in your .env file.")

print("MongoDB client initialized successfully.")
