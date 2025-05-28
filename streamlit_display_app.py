import streamlit as st

# Muss als erstes Streamlit-Kommando stehen!
st.set_page_config(page_title="Spielstand ansehen", layout="wide")

import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 🔄 Auto-Refresh alle 15 Sekunden
st_autorefresh(interval=15000, key="refresh_viewer")

# Firebase initialisieren
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.title("📊 Spielstand ansehen")

# Spielauswahl
spiele_docs = db.collection("spiele").stream()
spielnamen = sorted([doc.id for doc in spiele_docs])
spielname = st.selectbox("Spiel auswählen", spielnamen)

if not spielname:
    st.info("Bitte ein Spiel auswählen.")
    st.stop()

# Spieldaten laden
spiel_doc = db.collection("spiele").document(spielname).get()
if not spiel_doc.exists:
    st.error("Spiel nicht gefunden.")
    st.stop()

spiel = spiel_doc.to_dict()
spieler = spiel["spieler"]
runden = spiel["runden"]
multiplikatoren = spiel["multiplikatoren"]

# Punktberechnung
zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}
bonus_empfaenger_pro_runde = []

# Gewinne neu berechnen
for sp in spieler:
    sp["gewinne"] = []
    sp["punkte"] = 20.0

for runde_idx, runde in enumerate(runden):
    if runde_idx == 0:
        bonus_empfaenger = []
    else:
        min_punkte = min(zwischenpunkte.values())
        bonus_empfaenger = [name for name, punkte in zwischenpunkte.items() if punkte == min_punkte]
    bonus_empfaenger_pro_runde.append(bonus_empfaenger)

    for sp in spieler:
        name = sp["name"]
        einsatz = runde["einsaetze"].get(name, 0)
        platz = runde["plaetze"].get(name, 1)
        multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0

        gewinn = einsatz * multiplikator
        if name in bonus_empfaenger and multiplikator < 0:
            gewinn = 0  # Bonus-Regel

        sp["gewinne"].append(gewinn)
        zwischenpunkte[name] += gewinn

# Gesamtpunkte berechnen
for sp in spieler:
    sp["punkte"] = 20.0 + sum(sp["gewinne"])

# Tabelle anzeigen
daten = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
    for i in range(len(runden)):
        if i < len(sp["gewinne"]):
            bonus = bonus_empfaenger_pro_runde[i]
            bonus_symbol = "★" if bonus and sp["name"] in bonus else ""
            vorzeichen = "+" if sp["gewinne"][i] > 0 else ""
            rname = runden[i]["name"]
            zeile[rname] = (
                f"E: {runden[i]['einsaetze'].get(sp['name'], 1)} | "
                f"P: {runden[i]['plaetze'].get(sp['name'], 1)} | "
                f"{vorzeichen}{round(sp['gewinne'][i], 1)}{bonus_symbol}"
            )
    daten.append(zeile)

df = pd.DataFrame(daten)
st.dataframe(df, use_container_width=True, hide_index=True)
