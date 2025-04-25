from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import redis
import os
import json
import time

app = Flask(__name__)
CORS(app)

# MongoDB Setup with Retry
mongo_host = os.getenv("MONGO_HOST", "host.docker.internal")
mongo_port = int(os.getenv("MONGO_PORT", 27017))

for i in range(10):
    try:
        client = MongoClient(f"mongodb://{mongo_host}:{mongo_port}/", serverSelectionTimeoutMS=5000)
        client.admin.command("ping")  # test connection
        db = client.lab03
        collection = db.messages
        print("✅ Connected to MongoDB")
        break
    except ServerSelectionTimeoutError:
        print(f"❌ MongoDB not ready (attempt {i+1}/10), retrying in 5s...")
        time.sleep(5)
else:
    raise Exception("💥 Could not connect to MongoDB after 10 retries")

# Seed MongoDB if empty
if collection.count_documents({}) == 0:
    collection.insert_one({"message": "Hello from MongoDB with Redis cache!"})
    print("ℹ️ MongoDB seeded with initial message")

# Redis Setup
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

try:
    cache = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    cache.ping()
    print("✅ Connected to Redis")
except redis.exceptions.ConnectionError:
    print("⚠️ Redis not available, continuing without cache")
    cache = None

# API Endpoint
@app.route("/api/message", methods=["GET"])
def get_message():
    if cache:
        cached = cache.get("message")
        if cached:
            print("🔁 Returning cached response")
            return jsonify(json.loads(cached))

    doc = collection.find_one({}, {"_id": 0}) or {"message": "No data found"}

    if cache:
        cache.set("message", json.dumps(doc), ex=30)  # Cache for 30 seconds
        print("📦 Cached new response")

    return jsonify(doc)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
