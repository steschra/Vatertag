import streamlit as st
import pandas as pd
import uuid

st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Mehrnutzerfähige Spielverwaltung")

# Session-Variablen initialisieren
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
if "runde_aktualisiert" not in st.session_state:
    st.session_state.runde_aktualisiert = False

# Spiel Setup
if not st.session_state.spiel_started:
    st.header("Spiel Setup")
    spieler_input = st.text_area("Spielernamen (einer pro Zeile):")
    multiplikator_input = st.text_input("Multiplikatoren pro Platz (z.B. 3,2,1):")

    spiel_starten = st.button("Spiel starten")
    if spiel_starten:
        if spieler_input.strip() and multiplikator_input.strip():
            st.session_state.spieler = [
                {"name": name.strip(), "punkte": 20, "einsaetze": [], "plaetze": [], "gewinne": []}
                for name in spieler_input.strip().split("\n") if name.strip()
            ]
            st.session_state.multiplikatoren = [float(x.strip()) for x in multiplikator_input.split(",") if x.strip()]
            st.session_state.spiel_started = True
            st.session_state.runde_aktualisiert = False
        else:
            st.warning("Bitte Spieler und Multiplikatoren eingeben.")

# Spiel läuft
else:
    st.header("Rundenverwaltung")

    if st.button("Neue Runde starten"):
        st.session_state.runden.append({"name": f"Runde {len(st.session_state.runden)+1}", "einsaetze": {}, "plaetze": {}, "saved": False})
        st.session_state.runde_aktualisiert = False

    # Eingaben für jede Runde
    for idx, runde in enumerate(st.session_state.runden):
        with st.expander(f"{runde['name']}", expanded=(idx == len(st.session_state.runden) - 1)):
            runde["name"] = st.text_input(f"Name der Runde {idx+1}", value=runde["name"], key=f"name_{idx}")

            st.subheader("Einsätze eingeben")
            for sp in st.session_state.spieler:
                einsatz_key = f"einsatz_{idx}_{sp['name']}"
                einsatz = st.number_input(f"{sp['name']}: Einsatz", min_value=0, step=1,
                                          value=runde["einsaetze"].get(sp["name"], 0), key=einsatz_key)
                runde["einsaetze"][sp["name"]] = einsatz

            st.subheader("Platzierungen eingeben")
            for sp in st.session_state.spieler:
                platz_key = f"platz_{idx}_{sp['name']}"
                platz = st.number_input(f"{sp['name']}: Platz", min_value=1, step=1,
                                        value=runde["plaetze"].get(sp["name"], 1), key=platz_key)
                runde["plaetze"][sp["name"]] = platz

            if st.button(f"Runde {idx+1} speichern", key=f"save_{idx}"):
                runde["saved"] = True
                st.session_state.runde_aktualisiert = True

    # Punkte und Tabelle nur aktualisieren, wenn gespeichert wurde
    if st.session_state.runde_aktualisiert:
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
            sp["punkte"] = 20 + sum(g - e for g, e in zip(sp["gewinne"], sp["einsaetze"]))

        st.session_state.runde_aktualisiert = False  # Flag zurücksetzen

    # Anzeige Spielstand Tabelle
    st.header("Spielstand")

    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
        for i in range(len(st.session_state.runden) - 1, -1, -1):
            if i < len(sp["einsaetze"]):
                zeile[f"R{i+1}"] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
