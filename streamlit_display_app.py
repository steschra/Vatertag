import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 🔄 Auto-Refresh alle 15 Sekunden
st_autorefresh(interval=15000, key="refresh_viewer")

# 🔐 Spielname fest vorgeben (anstatt Auswahl)
FESTER_SPIELNAME = "Vatertagsrunde2025"  # <-- hier dein Spielname eintragen

# 🟡 Firestore initialisieren
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.set_page_config(page_title="Spielstand ansehen", layout="wide")
st.title(f"📊 Spielstand: {FESTER_SPIELNAME}")

# Daten abrufen
spiel_doc = db.collection("spiele").document(FESTER_SPIELNAME).get()
if not spiel_doc.exists:
    st.error("Spiel nicht gefunden.")
    st.stop()

daten = spiel_doc.to_dict()
spieler = daten["spieler"]
multiplikatoren = daten["multiplikatoren"]
runden = daten["runden"]

# Punktstand berechnen
zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}
bonus_empfaenger_pro_runde = []

for sp in spieler:
    sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []

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
            gewinn = 0

        sp["einsaetze"].append(einsatz)
        sp["plaetze"].append(platz)
        sp["gewinne"].append(float(gewinn))

    for sp in spieler:
        zwischenpunkte[sp["name"]] += sp["gewinne"][-1]

for sp in spieler:
    sp["punkte"] = 20.0 + sum(sp["gewinne"])

# Tabelle aufbereiten
daten_df = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
    for i in range(len(runden) - 1, -1, -1):
        runde = runden[i]
        if i < len(sp["einsaetze"]):
            bonus_symbol = "★" if bonus_empfaenger_pro_runde[i] and sp["name"] in bonus_empfaenger_pro_runde[i] else ""
            vorzeichen = "+" if sp['gewinne'][i] > 0 else ""
            zeile[runde["name"]] = (
                f"E: {int(sp['einsaetze'][i])} | "
                f"P: {sp['plaetze'][i]} | "
                f"{vorzeichen}{round(sp['gewinne'][i],1)}{bonus_symbol}"
            )
    daten_df.append(zeile)

df = pd.DataFrame(daten_df)
st.dataframe(df, use_container_width=True, hide_index=True)
