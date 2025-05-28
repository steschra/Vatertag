import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import altair as alt
import streamlit_autorefresh
import uuid

# Muss ganz früh kommen – noch vor allen anderen st.-Aufrufen!
st.set_page_config(page_title="📺 Live Spielstand", layout="wide")

# Auto-Refresh alle 5 Minuten (300.000 Millisekunden)
streamlit_autorefresh.st_autorefresh(interval=300_000, key="refresh")

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

# RUNDENVERWALTUNG
if st.session_state.spiel_started and st.session_state.spieler:
    
    st.header("Rundenverwaltung")
    st.text(f"Spielname: {st.session_state.spielname} \nMultiplikatoren: {st.session_state.multiplikatoren}")

    if st.button("Neue Runde starten"):
        st.session_state.runden.append({
            "name": f"Runde {len(st.session_state.runden)+1}",
            "einsaetze": {},
            "plaetze": {}
        })
        db.collection("spiele").document(st.session_state.spielname).update({
            "runden": st.session_state.runden
        })
        st.rerun()

    for i, runde in enumerate(st.session_state.runden):
        with st.expander(f"{runde['name']}", expanded=(i == len(st.session_state.runden) - 1)):
            rundenname_key = f"rundenname_{i}"
            neuer_name = st.text_input("Rundenname", value=runde["name"], key=rundenname_key)
            st.session_state.runden[i]["name"] = neuer_name

            st.subheader("Einsätze")
            for sp in st.session_state.spieler:
                einsatz_key = f"einsatz_{i}_{sp['name']}"
                if einsatz_key not in st.session_state:
                    st.session_state[einsatz_key] = runde["einsaetze"].get(sp["name"], 0)
                st.number_input(f"{sp['name']}: Einsatz", min_value=0, max_value=3, step=1, key=einsatz_key)
                runde["einsaetze"][sp["name"]] = st.session_state[einsatz_key]

            st.subheader("Platzierungen")
            for sp in st.session_state.spieler:
                platz_key = f"platz_{i}_{sp['name']}"
                if platz_key not in st.session_state:
                    st.session_state[platz_key] = runde["plaetze"].get(sp["name"], 1)
                st.number_input(f"{sp['name']}: Platz", min_value=1, step=1, key=platz_key)
                runde["plaetze"][sp["name"]] = st.session_state[platz_key]

    # Vor der Berechnung: Punktestand pro Spieler vor jeder Runde speichern
    zwischenpunkte = {sp["name"]: 20.0 for sp in st.session_state.spieler}
    bonus_empfaenger_pro_runde = []

    # Leere die Einträge
    for sp in st.session_state.spieler:
        sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []

    # Berechnung pro Runde
    for runde_idx, runde in enumerate(st.session_state.runden):
        # Bestimme Bonus-Empfänger (ab Runde 2)
        if runde_idx == 0:
            bonus_empfaenger = []
        else:
            min_punkte = min(zwischenpunkte.values())
            bonus_empfaenger = [name for name, punkte in zwischenpunkte.items() if punkte == min_punkte]
        bonus_empfaenger_pro_runde.append(bonus_empfaenger)

        # Berechne Gewinne
        for sp in st.session_state.spieler:
            name = sp["name"]
            einsatz = runde["einsaetze"].get(name, 0)
            platz = runde["plaetze"].get(name, 1)
            multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0

            gewinn = einsatz * multiplikator
            if name in bonus_empfaenger and multiplikator < 0:
                gewinn = 0  # Bonus für alle Letzten

            sp["einsaetze"].append(einsatz)
            sp["plaetze"].append(platz)
            sp["gewinne"].append(float(gewinn))

        # Update Zwischenpunkte für nächste Runde
        for sp in st.session_state.spieler:
            zwischenpunkte[sp["name"]] += sp["gewinne"][-1]

    # Aktualisiere Gesamtpunkte
    for sp in st.session_state.spieler:
        sp["punkte"] = 20.0 + sum(sp["gewinne"])

    # Spielstand
    st.header("Spielstand")
    daten = []
    # Spieler mit Bonus pro Runde ermitteln
    bonus_empfaenger_pro_runde = []
    punkte_zwischen_runden = [ {sp["name"]: 20.0} for sp in st.session_state.spieler ]  # Startpunkte

    zwischenpunkte = {sp["name"]: 20.0 for sp in st.session_state.spieler}
    for runde_idx, runde in enumerate(st.session_state.runden):
        if runde_idx == 0:
            # In der ersten Runde kein Bonus
            bonus_empfaenger_pro_runde.append(None)
        else:
            min_punkte = min(zwischenpunkte.values())
            letzte_spieler = [name for name, punkte in zwischenpunkte.items() if punkte == min_punkte]
            bonus_empfaenger_pro_runde.append(letzte_spieler)

        # Punktestand für nächste Runde aktualisieren
        for sp in st.session_state.spieler:
            zwischenpunkte[sp["name"]] += sp["gewinne"][runde_idx]

# Verlaufsgrafik
st.subheader("📈 Punkteverlauf")
df_chart = pd.DataFrame(punkteverlauf)

# Nur Runden bis zur vorletzten Runde behalten
max_runden_index = len(runden) - 2  # da 0-basiert, -2 = vorletzte Runde
# Runde ist String wie "1: XYZ", wir filtern nach der Rundenzahl vor dem Doppelpunkt

df_chart = df_chart[df_chart["Runde"].apply(
    lambda r: int(r.split(":")[0]) <= max_runden_index + 1  # +1 da Runde 1-basiert
)]

chart = alt.Chart(df_chart).mark_line(point=True).encode(
    x="Runde",
    y=alt.Y("Punkte", scale=alt.Scale(zero=False)),
    color="Spieler",
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)
aktuelle_runde_index = len(runden) - 1  # Index der letzten Runde (0-basiert)
aktuelle_runde_name = f"{len(runden)}: {runden[-1]['name']}"

