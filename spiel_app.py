# spiel_app.py – Streamlit Spielverwaltung für mehrere Nutzer mit Rundeneingabe in logischer Reihenfolge und Rundenspeicherung
import streamlit as st
import pandas as pd
import uuid

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
if "runde_inputs" not in st.session_state:
    st.session_state.runde_inputs = {}

# SPIEL STARTEN
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

# SPIEL LOGIK
else:
    st.header("Rundenverwaltung")

    if st.button("Neue Runde starten"):
        neue_runde_id = len(st.session_state.runden)
        st.session_state.runde_inputs[neue_runde_id] = {"name": f"Runde {neue_runde_id+1}", "einsaetze": {}, "plaetze": {}}

    gespeicherte_runden = []

    for echte_index in range(len(st.session_state.runde_inputs)):
        inputs = st.session_state.runde_inputs[echte_index]
        with st.expander(f"{inputs['name']}", expanded=(echte_index == len(st.session_state.runde_inputs)-1)):
            inputs["name"] = st.text_input(f"Name der Runde {echte_index+1}", value=inputs["name"], key=f"name_{echte_index}")

            st.subheader("Einsätze eingeben")
            for sp in st.session_state.spieler:
                einsatz_key = f"einsatz_{echte_index}_{sp['name']}"
                einsatz = st.number_input(f"{sp['name']}: Einsatz", min_value=0, step=1,
                                          value=inputs["einsaetze"].get(sp["name"], 0), key=einsatz_key)
                inputs["einsaetze"][sp["name"]] = einsatz

            st.subheader("Platzierungen eingeben")
            for sp in st.session_state.spieler:
                platz_key = f"platz_{echte_index}_{sp['name']}"
                platz = st.number_input(f"{sp['name']}: Platz", min_value=1, step=1,
                                        value=inputs["plaetze"].get(sp["name"], 1), key=platz_key)
                inputs["plaetze"][sp["name"]] = platz

            if st.button(f"Runde {echte_index+1} speichern", key=f"save_{echte_index}"):
                st.session_state.runden.append(inputs)
                for sp in st.session_state.spieler:
                    einsatz = inputs["einsaetze"].get(sp["name"], 0)
                    platz = inputs["plaetze"].get(sp["name"], 1)
                    multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0
                    gewinn = int(einsatz * multiplikator)
                    sp["einsaetze"].append(einsatz)
                    sp["plaetze"].append(platz)
                    sp["gewinne"].append(gewinn)
                gespeicherte_runden.append(echte_index)

    # Nach dem Speichern die Eingaben löschen
    for idx in gespeicherte_runden:
        if idx in st.session_state.runde_inputs:
            del st.session_state.runde_inputs[idx]

    # Punktestand berechnen
    for sp in st.session_state.spieler:
        sp["punkte"] = 20 + sum(g - e for g, e in zip(sp["gewinne"], sp["einsaetze"]))

    # TABELLE
    st.header("Spielstand")
    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
        for i in range(len(st.session_state.runden)-1, -1, -1):
            if i < len(sp["einsaetze"]):
                zeile[f"R{i+1}"] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
