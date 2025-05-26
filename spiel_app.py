# spiel_app.py – Streamlit Spielverwaltung für mehrere Nutzer
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
        st.session_state.runden.append({"name": f"Runde {len(st.session_state.runden)+1}", "einsaetze": {}, "plaetze": {}})

    for runden_index, runde in enumerate(st.session_state.runden[::-1]):
        echte_index = len(st.session_state.runden) - 1 - runden_index

        with st.expander(f"{runde['name']}", expanded=(runden_index == 0)):
            # Schritt 1: Name, Einsätze und Platzierungen gleichzeitig
            runde["name"] = st.text_input(f"Name der Runde {echte_index+1}", value=runde["name"], key=f"name_{echte_index}")

            st.subheader("Einsatz und Platzierung")
            for sp in st.session_state.spieler:
                einsatz_key = f"einsatz_{echte_index}_{sp['name']}"
                platz_key = f"platz_{echte_index}_{sp['name']}"
                runde["einsaetze"][sp["name"]] = st.number_input(f"{sp['name']}: Einsatz", min_value=0, value=runde["einsaetze"].get(sp["name"], 0), step=1, key=einsatz_key)
                runde["plaetze"][sp["name"]] = st.number_input(f"{sp['name']}: Platz", min_value=1, value=runde["plaetze"].get(sp["name"], 1), step=1, key=platz_key)

            # Berechnung
            for sp in st.session_state.spieler:
                einsatz = runde["einsaetze"].get(sp["name"], 0)
                platz = runde["plaetze"].get(sp["name"], 1)
                multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0
                gewinn = einsatz * multiplikator

                if len(sp["einsaetze"]) <= echte_index:
                    sp["einsaetze"].append(einsatz)
                    sp["plaetze"].append(platz)
                    sp["gewinne"].append(gewinn)
                else:
                    sp["einsaetze"][echte_index] = einsatz
                    sp["plaetze"][echte_index] = platz
                    sp["gewinne"][echte_index] = gewinn

    # Punktestand berechnen
    for sp in st.session_state.spieler:
        sp["punkte"] = 20 + sum(g - e for g, e in zip(sp["gewinne"], sp["einsaetze"]))

    # TABELLE
    st.header("Spielstand")
    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": sp["punkte"]}
        for i in range(len(st.session_state.runden)):
            if i < len(sp["einsaetze"]):
                zeile[f"R{i+1}"] = f"E: {sp['einsaetze'][i]} | P: {sp['plaetze'][i]} | +{sp['gewinne'][i]:.1f}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
