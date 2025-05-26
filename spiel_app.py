# spiel_app.py – Mehrbenutzerfähige Spielverwaltung mit editierbaren Runden
import streamlit as st
import pandas as pd
import uuid

# Seiteneinstellungen
st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Mehrnutzerfähige Spielverwaltung")

# Session-Initialisierung
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

# SPIEL VERWALTUNG
else:
    st.header("Rundenverwaltung")

    st.button("Neue Runde starten", on_click=lambda: st.session_state.runden.append({
        "name": f"Runde {len(st.session_state.runden) + 1}",
        "einsaetze": {}, "plaetze": {}
    }))

    # Zurücksetzen der Daten für Berechnung
    for sp in st.session_state.spieler:
        sp["einsaetze"] = []
        sp["plaetze"] = []
        sp["gewinne"] = []

    # Runden anzeigen (umgekehrte Reihenfolge)
    for echte_index in reversed(range(len(st.session_state.runden))):
        runde = st.session_state.runden[echte_index]

        rundenname_key = f"name_{echte_index}"
        runde["name"] = st.text_input(f"Name der Runde {echte_index+1}", value=runde["name"], key=rundenname_key)

        with st.expander(runde["name"], expanded=(echte_index == len(st.session_state.runden) - 1)):
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

    # Punkte berechnen (nur Gewinne addieren zu Startpunkten)
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
                rundenname = st.session_state.runden[i]["name"]
                zeile[rundenname] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
