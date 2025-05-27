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

    col1, col2 = st.columns([0.2,0.2])
    with col1:
        buttonLaden = st.button("Spiel laden / starten")
    with col2:
        buttonLöschen = st.button('Spiel löschen')
        
    if buttonLaden and spielname:
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
    
    if buttonLöschen and spielname:
        st.session_state.spielname = spielname
        db.collection("spiele").document(spielname).delete()
        st.success("Spiel gelöscht")
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
                einsatz = st.number_input(f"{sp['name']}: Einsatz", min_value=1, max_value=3, step=1,
                                          value=runde["einsaetze"].get(sp["name"], 1), key=einsatz_key)
                runde["einsaetze"][sp["name"]] = einsatz

            st.subheader("Platzierungen")
            for sp in st.session_state.spieler:
                platz_key = f"platz_{i}_{sp['name']}"
                platz = st.number_input(f"{sp['name']}: Platz", min_value=1, step=1,
                                        value=runde["plaetze"].get(sp["name"], 1), key=platz_key)
                runde["plaetze"][sp["name"]] = platz

    # Berechnung mit doppelten Punkten pro Runde für jeweils den Letzten
    for sp in st.session_state.spieler:
        sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
        sp["punkte"] = 20.0  # Startwert

    for i, runde in enumerate(st.session_state.runden):
        # Punkte vor dieser Runde berechnen
        punkte_vor_runde = {sp["name"]: sp["punkte"] for sp in st.session_state.spieler}
        letzter_spieler = min(punkte_vor_runde, key=punkte_vor_runde.get)

        for sp in st.session_state.spieler:
            einsatz = runde["einsaetze"].get(sp["name"], 0)
            platz = runde["plaetze"].get(sp["name"], 1)
            multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0

            if sp["name"] == letzter_spieler:
                multiplikator *= 2

            gewinn = float(einsatz * multiplikator)
            sp["einsaetze"].append(einsatz)
            sp["plaetze"].append(platz)
            sp["gewinne"].append(gewinn)
            sp["punkte"] += gewinn

    # Rundung
    for sp in st.session_state.spieler:
        sp["punkte"] = round(sp["punkte"], 2)
   
    # Spielstand
    st.header("Spielstand")
    daten = []
    # Spieler mit Bonus pro Runde ermitteln
    bonus_empfaenger_pro_runde = []
    punkte_zwischen_runden = [ {sp["name"]: 20.0} for sp in st.session_state.spieler ]  # Startpunkte

    zwischenpunkte = {sp["name"]: 20.0 for sp in st.session_state.spieler}
    for runde_idx, runde in enumerate(st.session_state.runden
        if runde_idx == 0:
            # In der ersten Runde kein Bonus
            bonus_empfaenger_pro_runde.append(None)
        else:
            # Spieler mit dem niedrigsten Punktestand vor der Runde
            letzter_spieler = min(zwischenpunkte, key=zwischenpunkte.get)
            bonus_empfaenger_pro_runde.append(letzter_spieler)

        # Punktestand für nächste Runde aktualisieren
        for sp in st.session_state.spieler:
            zwischenpunkte[sp["name"]] += sp["gewinne"][runde_idx]
            
    # Anzeige
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"],1)}
        for i in range(len(st.session_state.runden) - 1, -1, -1):
            runde = st.session_state.runden[i]
            if i < len(sp["einsaetze"]):
                bonus_symbol = "*" if sp["name"] == bonus_empfaenger_pro_runde[i] else ""
                zeile[runde["name"]] = (
                    f"E: {int(sp['einsaetze'][i])} | "
                    f"P: {sp['plaetze'][i]} | "
                    f"+{round(sp['gewinne'][i],1)}{bonus_symbol}"
                )
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True, hide_index=True)


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
