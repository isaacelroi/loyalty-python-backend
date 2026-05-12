from mongoengine import connect
from config import MONGO_URI

def init_db():
    connect(host=MONGO_URI)
