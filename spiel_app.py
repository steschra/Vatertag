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

    st.button("Neue Runde starten", on_click=lambda: st.session_state.runden.append({
        "name": f"Runde {len(st.session_state.runden)+1}",
        "einsaetze": {},
        "plaetze": {}
    }))

    # Reset Punktelisten
    for sp in st.session_state.spieler:
        sp["einsaetze"] = []
        sp["plaetze"] = []
        sp["gewinne"] = []

    for echte_index, runde in enumerate(st.session_state.runden):
        with st.expander(f"Runde {echte_index+1}", expanded=(echte_index == len(st.session_state.runden) - 1)):
            # Rundenname editierbar innerhalb des Expanders
            neuer_name = st.text_input("Rundenname", value=runde["name"], key=f"rundenname_{echte_index}")
            runde["name"] = neuer_name
            st.markdown(f"**Aktueller Rundenname:** {runde['name']}")

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

    # Punkte berechnen
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
                zeile[rname] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
