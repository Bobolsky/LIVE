import os
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

# Inizializzazione di Firebase
cred = credentials.Certificate(os.environ.get("FIREBASE_KEY_PATH", "serviceAccountKey.json"))
firebase_admin.initialize_app(cred)
db = firestore.client()
