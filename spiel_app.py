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

# Seiteneinstellungen
st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Mehrnutzerfähige Spielverwaltung")

# Initialisierung der Session-Variablen
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "spieler" not in st.session_state:
    st.session_state.spieler = []
if "multiplikatoren" not in st.session_state:
    st.session_state.multiplikatoren = []
if "runden" not in st.session_state:
    st.session_state.runden = []
if "spiel_started" not in st.session_state:
    st.session_state.spiel_started = False

# Vorhandene Spiele aus Firestore abrufen
spiel_dokumente = db.collection("spiele").stream()
spielnamen = [doc.id for doc in spiel_dokumente]

# Ladeoption, nur wenn noch kein Spiel gestartet wurde
if not st.session_state.spiel_started:
    st.subheader("Vorhandenes Spiel laden")
    spiel_zum_laden = st.selectbox("Wähle ein Spiel aus", options=spielnamen)
    if st.button("Spiel laden"):
        try:
            doc = db.collection("spiele").document(spiel_zum_laden).get()
            if doc.exists:
                daten = doc.to_dict()
                st.session_state.spieler = daten["spieler"]
                st.session_state.multiplikatoren = daten["multiplikatoren"]
                st.session_state.runden = daten["runden"]
                st.session_state.spiel_started = True
                st.session_state.spielname = spiel_zum_laden
                st.rerun()
            else:
                st.warning("Dokument nicht gefunden.")
        except Exception as e:
            st.error(f"Fehler beim Laden: {e}")

    # Spielname eingeben
    spielname = st.text_input("Spielname eingeben (Pflicht für Speicherung)", key="spielname")
    
    st.subheader("Neues Spiel Setup")
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

    for echte_index, runde in enumerate(st.session_state.runden):
        with st.expander(f"{runde['name']}", expanded=(echte_index == len(st.session_state.runden)-1)):
            neuer_name = st.text_input(f"Name der Runde {echte_index+1}", value=runde["name"], key=f"name_{echte_index}")
            runde["name"] = neuer_name

            st.subheader("Einsätze eingeben")
            for sp in st.session_state.spieler:
                einsatz_key = f"einsatz_{echte_index}_{sp['name']}"
                einsatz = st.number_input(f"{sp['name']}: Einsatz", min_value=0, step=1,
                                          value=runde["einsaetze"].get(sp["name"], 0), key=einsatz_key)
                runde["einsaetze"][sp["name"]] = einsatz

            st.subheader("Platzierungen eingeben")
            for sp in st.session_state.spieler:
                platz_key = f"platz_{echte_index}_{sp['name']}"
                platz = st.number_input(f"{sp['name']}: Platz", min_value=1, step=1,
                                        value=runde["plaetze"].get(sp["name"], 1), key=platz_key)
                runde["plaetze"][sp["name"]] = platz

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
        sp["punkte"] = 20 + sum(sp["gewinne"])

    # TABELLE
    st.header("Spielstand")
    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
        for i in range(len(st.session_state.runden)-1, -1, -1):
            if i < len(sp["einsaetze"]):
                rname = st.session_state.runden[i]["name"]
                zeile[f"{rname}"] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)

    # AUTOMATISCHES SPEICHERN
    if spielname:
        try:
            spiel_daten = {
                "spieler": st.session_state.spieler,
                "multiplikatoren": st.session_state.multiplikatoren,
                "runden": st.session_state.runden,
                "zeitstempel": firestore.SERVER_TIMESTAMP
            }
            db.collection("spiele").document(spielname).set(spiel_daten)
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")            
