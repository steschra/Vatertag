import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Firebase initialisieren
if "firebase_initialized" not in st.session_state:
    try:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        st.session_state.firebase_initialized = True
        st.success("Firebase verbunden!")
    except Exception as e:
        st.error(f"Fehler bei der Firebase-Verbindung: {e}")
        st.stop()

# Firestore-Client
db = firestore.client()

# Test-Daten schreiben
st.subheader("Firestore Test")

if st.button("Test-Dokument schreiben"):
    doc_ref = db.collection("tests").document("streamlit_test")
    doc_ref.set({
        "text": "Hallo Firestore!",
        "zahl": 123,
    })
    st.success("Dokument gespeichert.")

# Test-Daten lesen
if st.button("Test-Dokument lesen"):
    doc = db.collection("tests").document("streamlit_test").get()
    if doc.exists:
        st.json(doc.to_dict())
    else:
        st.warning("Dokument nicht gefunden.")
