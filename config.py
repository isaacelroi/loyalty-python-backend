import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://loyalty_app:e1C50tK0iOfj2e8j@cluster0.iyq9xso.mongodb.net/loyalty_app?retryWrites=true&w=majority"
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis_app")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
