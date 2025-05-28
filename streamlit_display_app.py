import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd

# 🔄 Auto-Refresh alle 15 Sekunden
st_autorefresh(interval=15000, key="refresh_viewer")

# Firestore initialisieren (einmalig)
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.set_page_config(page_title="Spielstand ansehen", layout="wide")
st.title("Spielstand ansehen")

# Spiel auswählen
spiele_docs = db.collection("spiele").stream()
spielnamen = sorted([doc.id for doc in spiele_docs])
spielname = st.selectbox("Spiel auswählen", spielnamen)

if spielname:
    spiel_doc = db.collection("spiele").document(spielname).get()
    if not spiel_doc.exists:
        st.error("Spiel nicht gefunden.")
        st.stop()

    daten = spiel_doc.to_dict()
    spieler = daten.get("spieler", [])
    multiplikatoren = daten.get("multiplikatoren", [])
    runden = daten.get("runden", [])

    if not spieler or not runden:
        st.info("Spiel hat keine Spieler oder Runden.")
        st.stop()

    # Punkte berechnen (zur Sicherheit)
    for sp in spieler:
        sp["punkte"] = 20.0 + sum(sp.get("gewinne", []))

    # Tabelle aufbauen
    tabelle = []
    for sp in sorted(spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
        for i in range(len(runden) - 1, -1, -1):
            runde = runden[i]
            bonus_empfaenger = runde.get("bonus_empfaenger", [])
            bonus_empfaenger = bonus_empfaenger if bonus_empfaenger is not None else []
            bonus_symbol = "★" if sp["name"] in bonus_empfaenger else ""
            
            einsatz = sp.get("einsaetze", [])[i] if i < len(sp.get("einsaetze", [])) else "-"
            platz = sp.get("plaetze", [])[i] if i < len(sp.get("plaetze", [])) else "-"
            gewinn = sp.get("gewinne", [])[i] if i < len(sp.get("gewinne", [])) else "-"
            vorzeichen = "+" if isinstance(gewinn, (int, float)) and gewinn > 0 else ""

            zeile[runde["name"]] = f"E: {einsatz} | P: {platz} | {vorzeichen}{gewinn}{bonus_symbol}"
        tabelle.append(zeile)

    df = pd.DataFrame(tabelle)
    st.dataframe(df, use_container_width=True, hide_index=True)
