import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import altair as alt

# 🔒 Fester Spielname – HIER ANPASSEN!
FESTER_SPIELNAME = "Vatertagsspiele 2025"

# Firebase verbinden
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.set_page_config(page_title="📺 Live Spielstand", layout="wide")
st.title("🎲 Vatertagsspiele 2025 - Spielstand (live)")

# Spiel laden
spiel_doc = db.collection("spiele").document(FESTER_SPIELNAME).get()
if not spiel_doc.exists:
    st.error(f"Spiel '{FESTER_SPIELNAME}' nicht gefunden.")
    st.stop()

daten = spiel_doc.to_dict()
spieler = daten["spieler"]
multiplikatoren = daten["multiplikatoren"]
runden = daten["runden"]

# Punkte berechnen
for sp in spieler:
    sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
    sp["punkte"] = 20.0

punkteverlauf = []
zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}
bonus_empfaenger_pro_runde = []

for i, runde in enumerate(runden):
    letzter_spieler = min(zwischenpunkte, key=zwischenpunkte.get)
    bonus_empfaenger_pro_runde.append(letzter_spieler)

    for sp in spieler:
        einsatz = runde["einsaetze"].get(sp["name"], 0)
        platz = runde["plaetze"].get(sp["name"], 1)
        multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0
        if sp["name"] == letzter_spieler:
            multiplikator *= 1
        gewinn = einsatz * multiplikator
        sp["einsaetze"].append(einsatz)
        sp["plaetze"].append(platz)
        sp["gewinne"].append(gewinn)
        sp["punkte"] += gewinn
        zwischenpunkte[sp["name"]] += gewinn
        punkteverlauf.append({
            "Runde": f"{i+1}: {runde['name']}",
            "Spieler": sp["name"],
            "Punkte": zwischenpunkte[sp["name"]]
        })

# Punktetabelle anzeigen
st.subheader("📊 Aktueller Punktestand")
tabelle = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
   # for i in range(len(runden)):
    for i in range(len(runden) - 1, -1, -1):
        bonus = "*" if sp["name"] == bonus_empfaenger_pro_runde[i] else ""
        zeile[runden[i]["name"]] = f"E: {sp['einsaetze'][i]} | P: {sp['plaetze'][i]} | +{round(sp['gewinne'][i],1)}{bonus}"
    tabelle.append(zeile)

df = pd.DataFrame(tabelle)
st.dataframe(df, use_container_width=True, hide_index=True)

# Verlaufsgrafik
st.subheader("📈 Punkteverlauf")
df_chart = pd.DataFrame(punkteverlauf)
chart = alt.Chart(df_chart).mark_line(point=True).encode(
    x="Runde",
    y=alt.Y("Punkte", scale=alt.Scale(zero=False)),
    color="Spieler",
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)
