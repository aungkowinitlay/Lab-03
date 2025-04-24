from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import redis
import os
import json

app = Flask(__name__)
CORS(app)

# MongoDB setup
mongo_host = os.getenv("MONGO_HOST", "mongo")
mongo_port = int(os.getenv("MONGO_PORT", 27017))
client = MongoClient(f"mongodb://{mongo_host}:{mongo_port}/")
db = client.lab03
collection = db.messages

# Seed MongoDB if empty
if collection.count_documents({}) == 0:
    collection.insert_one({"message": "Hello from MongoDB with Redis cache!"})

# Redis setup
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", 6379))
cache = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

@app.route("/api/message", methods=["GET"])
def get_message():
    cached = cache.get("message")
    
    if cached:
        return jsonify(json.loads(cached))  # Return from cache

    doc = collection.find_one({}, {"_id": 0}) or {"message": "No data found"}
    
    # Save to cache for next request
    cache.set("message", json.dumps(doc), ex=30)  # expires in 30s
    return jsonify(doc)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
