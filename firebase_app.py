import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.title("Firebase Firestore Verbindungs-Test")

# Pfad zum Service-Account JSON anpassen
SERVICE_ACCOUNT_PATH = "pfad/zur/deiner/serviceAccountKey.json"

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try:
    db = init_firebase()
    st.success("Firebase initialisiert.")

    # Test: Mindestens ein Dokument aus der Collection 'spiele' holen
    docs = list(db.collection("spiele").limit(1).stream())
    if docs:
        for doc in docs:
            st.write(f"Dokument gefunden: ID={doc.id}, Daten={doc.to_dict()}")
    else:
        st.warning("Verbindung OK, aber keine Dokumente in der Collection 'spiele' gefunden.")
except Exception as e:
    st.error(f"Fehler bei der Firebase-Verbindung: {e}")
