import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import uuid

# Firebase initialisieren
if "firebase_initialized" not in st.session_state:
    try:
        cred = credentials.Certificate(json.loads(st.secrets["firebase_service_account"]))
        firebase_admin.initialize_app(cred)
        st.session_state.firebase_initialized = True
    except Exception as e:
        st.error(f"Firebase-Fehler: {e}")
        st.stop()

db = firestore.client()

# Streamlit UI
st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Mehrnutzerfähige Spielverwaltung")

# SPIELNAME wählen
spielname = st.text_input("Spielname eingeben", key="spielname_input")

if "spieler" not in st.session_state:
    st.session_state.spieler = []
if "multiplikatoren" not in st.session_state:
    st.session_state.multiplikatoren = []
if "runden" not in st.session_state:
    st.session_state.runden = []
if "spiel_started" not in st.session_state:
    st.session_state.spiel_started = False

# Spiel speichern und laden
col1, col2 = st.columns(2)
with col1:
    if st.button("Spiel speichern"):
        if not spielname:
            st.warning("Bitte Spielname angeben.")
        else:
            data = {
                "spieler": st.session_state.spieler,
                "multiplikatoren": st.session_state.multiplikatoren,
                "runden": st.session_state.runden,
            }
            db.collection("spiele").document(spielname).set(data)
            st.success(f"Spiel '{spielname}' gespeichert.")

with col2:
    if st.button("Spiel laden"):
        if not spielname:
            st.warning("Bitte Spielname angeben.")
        else:
            doc = db.collection("spiele").document(spielname).get()
            if doc.exists:
                data = doc.to_dict()
                st.session_state.spieler = data.get("spieler", [])
                st.session_state.multiplikatoren = data.get("multiplikatoren", [])
                st.session_state.runden = data.get("runden", [])
                st.session_state.spiel_started = True
                st.success(f"Spiel '{spielname}' geladen!")
                st.rerun()
            else:
                st.error("Spiel nicht gefunden.")

# SPIEL SETUP
if not st.session_state.spiel_started:
    st.header("Spiel Setup")
    spieler_input = st.text_area("Spielernamen (einer pro Zeile):")
    multiplikator_input = st.text_input("Multiplikatoren pro Platz (z. B. 3,2,1):")

    if st.button("Spiel starten"):
        st.session_state.spieler = [
            {"name": name.strip(), "punkte": 20, "einsaetze": [], "plaetze": [], "gewinne": []}
            for name in spieler_input.strip().split("\n") if name.strip()
        ]
        st.session_state.multiplikatoren = [float(x.strip()) for x in multiplikator_input.split(",") if x.strip()]
        st.session_state.spiel_started = True
        st.rerun()

else:
    st.header("Rundenverwaltung")

    if st.button("Neue Runde starten"):
        st.session_state.runden.append({
            "name": f"Runde {len(st.session_state.runden)+1}",
            "einsaetze": {},
            "plaetze": {}
        })

    for i, runde in enumerate(st.session_state.runden):
        with st.expander(runde["name"], expanded=(i == len(st.session_state.runden)-1)):
            neuer_name = st.text_input(f"Name der Runde {i+1}", value=runde["name"], key=f"runde_name_{i}")
            runde["name"] = neuer_name

            st.subheader("Einsätze")
            for sp in st.session_state.spieler:
                runde["einsaetze"][sp["name"]] = st.number_input(
                    f"{sp['name']}: Einsatz", min_value=0, step=1,
                    value=runde["einsaetze"].get(sp["name"], 0), key=f"einsatz_{i}_{sp['name']}"
                )

            st.subheader("Platzierungen")
            for sp in st.session_state.spieler:
                runde["plaetze"][sp["name"]] = st.number_input(
                    f"{sp['name']}: Platz", min_value=1, step=1,
                    value=runde["plaetze"].get(sp["name"], 1), key=f"platz_{i}_{sp['name']}"
                )

    # Punkte neu berechnen
    for sp in st.session_state.spieler:
        sp["einsaetze"] = []
        sp["plaetze"] = []
        sp["gewinne"] = []

    for runde in st.session_state.runden:
        for sp in st.session_state.spieler:
            einsatz = runde["einsaetze"].get(sp["name"], 0)
            platz = runde["plaetze"].get(sp["name"], 1)
            multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0
            gewinn = int(einsatz * multiplikator)
            sp["einsaetze"].append(einsatz)
            sp["plaetze"].append(platz)
            sp["gewinne"].append(gewinn)

    for sp in st.session_state.spieler:
        sp["punkte"] = 20 + sum(sp["gewinne"])  # Nur Gewinne zählen

    # Tabelle
    st.header("Spielstand")
    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
        for j in range(len(st.session_state.runden)-1, -1, -1):
            if j < len(sp["einsaetze"]):
                rname = st.session_state.runden[j]["name"]
                zeile[rname] = f"E: {int(sp['einsaetze'][j])} | P: {sp['plaetze'][j]} | +{int(sp['gewinne'][j])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
