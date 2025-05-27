import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import uuid

def get_firestore_client():
    # Prüfen, ob eine Firebase-App bereits initialisiert wurde
    if not firebase_admin._apps:
        # Aus st.secrets laden (secrets.toml oder Streamlit Cloud)
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    # Firestore-Client zurückgeben
    return firestore.client()

db = get_firestore_client()

# Spiel laden oder neues starten
st.set_page_config(page_title="Vatertagsspiele", layout="wide")
st.title("Vatertagsspiele")

if "spiel_started" not in st.session_state:
    st.session_state.spiel_started = False
if "spielname" not in st.session_state:
    st.session_state.spielname = None

# SPIEL LADEN ODER STARTEN
if not st.session_state.spiel_started:
    st.subheader("Spielname eingeben oder auswählen")

    # Vorhandene Spiele laden
    spiele_docs = db.collection("spiele").stream()
    spielnamen = sorted([doc.id for doc in spiele_docs])

    optionen = ["Neues Spiel erstellen"] + spielnamen
    auswahl = st.selectbox("Spiel auswählen", optionen)

    if auswahl == "Neues Spiel erstellen":
        spielname = st.text_input("Neuer Spielname")
    else:
        spielname = auswahl

    if st.button("Spiel laden / starten") and spielname:
        st.session_state.spielname = spielname

        if auswahl != "Neues Spiel erstellen":
            # Vorhandenes Spiel laden
            spiel_doc = db.collection("spiele").document(spielname).get()
            if spiel_doc.exists:
                daten = spiel_doc.to_dict()
                st.session_state.spieler = daten["spieler"]
                st.session_state.multiplikatoren = daten["multiplikatoren"]
                st.session_state.runden = daten["runden"]
            else:
                st.error("Spiel nicht gefunden.")
                st.stop()
        else:
            st.session_state.spieler = []
            st.session_state.multiplikatoren = []
            st.session_state.runden = []

        st.session_state.spiel_started = True
        st.rerun()

# SPIEL SETUP
if st.session_state.spiel_started and not st.session_state.spieler:
    st.header("Spiel Setup")
    st.text(f"Aktueller Spielname: {st.session_state.spielname}")

    spieler_input = st.text_area("Spielernamen (einer pro Zeile):")
    multiplikator_input = st.text_input("Multiplikatoren pro Platz (z. B. 3,2,1):")

    if st.button("Setup speichern"):
        st.session_state.spieler = [
            {"name": name.strip(), "punkte": 20, "einsaetze": [], "plaetze": [], "gewinne": []}
            for name in spieler_input.strip().split("\n") if name.strip()
        ]
        st.session_state.multiplikatoren = [float(x.strip()) for x in multiplikator_input.split(",") if x.strip()]
        st.session_state.runden = []
        db.collection("spiele").document(st.session_state.spielname).set({
            "spieler": st.session_state.spieler,
            "multiplikatoren": st.session_state.multiplikatoren,
            "runden": st.session_state.runden
        })
        st.success("Spiel gespeichert.")
        st.rerun()

# SPIELVERWALTUNG
if st.session_state.spiel_started and st.session_state.spieler:
    
    st.header(f"Aktueller Spielname: {st.session_state.spielname} - Multiplikatoren: st.session_state.multiplikatoren")
    st.subheader("Rundenverwaltung")

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
                einsatz = st.number_input(f"{sp['name']}: Einsatz", min_value=1, max_value=3, step=1,
                                          value=runde["einsaetze"].get(sp["name"], 1), key=einsatz_key)
                runde["einsaetze"][sp["name"]] = einsatz

            st.subheader("Platzierungen")
            for sp in st.session_state.spieler:
                platz_key = f"platz_{i}_{sp['name']}"
                platz = st.number_input(f"{sp['name']}: Platz", min_value=1, step=1,
                                        value=runde["plaetze"].get(sp["name"], 1), key=platz_key)
                runde["plaetze"][sp["name"]] = platz

    # Berechnung
    for sp in st.session_state.spieler:
        sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
        for runde in st.session_state.runden:
            einsatz = runde["einsaetze"].get(sp["name"], 0)
            platz = runde["plaetze"].get(sp["name"], 1)
            multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0
            gewinn = int(einsatz * multiplikator)
            sp["einsaetze"].append(einsatz)
            sp["plaetze"].append(platz)
            sp["gewinne"].append(gewinn)
        sp["punkte"] = 20 + sum(sp["gewinne"])

    # Spielstand
    st.header("Spielstand")
    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
        for i in range(len(st.session_state.runden) - 1, -1, -1):
            runde = st.session_state.runden[i]
            if i < len(sp["einsaetze"]):
                zeile[runde["name"]] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)


    # AUTOMATISCHES SPEICHERN
    if "spielname" in st.session_state:
        try:
            spiel_daten = {
                "spieler": st.session_state.spieler,
                "multiplikatoren": st.session_state.multiplikatoren,
                "runden": st.session_state.runden,
                "zeitstempel": firestore.SERVER_TIMESTAMP
            }
            db.collection("spiele").document(st.session_state.spielname).set(spiel_daten)
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")            
