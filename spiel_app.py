import streamlit as st
import pandas as pd

st.set_page_config(page_title="Spielverwaltung (editierbare Runden)", layout="wide")
st.title("Spielverwaltung mit editierbaren, eingeklappten Runden")

# Initialisierung Session State
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

# --- Spiel Setup ---
if not st.session_state.spiel_started:
    st.header("Spiel Setup")
    spieler_input = st.text_area("Spielernamen (je eine pro Zeile):")
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

# --- Spiel läuft ---
else:
    st.header("Rundenverwaltung")

    if st.button("Neue Runde starten"):
        st.session_state.runden.append({
            "name": f"Runde {len(st.session_state.runden)+1}",
            "einsaetze": {},
            "plaetze": {},
            "saved": False
        })
        st.session_state.runde_aktualisiert = False

    # Alle Runden anzeigen (eingeklappt), Eingabefelder editierbar
    for idx, runde in enumerate(st.session_state.runden):
        with st.expander(f"{runde['name']} {'(gespeichert)' if runde['saved'] else '(nicht gespeichert)'}", expanded=False):
            # Runde Name editierbar
            neue_name = st.text_input(f"Name der Runde {idx+1}", value=runde["name"], key=f"rundenname_{idx}")
            runde["name"] = neue_name

            st.subheader("Einsätze")
            for sp in st.session_state.spieler:
                einsatz = st.number_input(f"{sp['name']} Einsatz (Runde {idx+1})",
                                         min_value=0, step=1,
                                         value=runde["einsaetze"].get(sp["name"], 0),
                                         key=f"einsatz_{idx}_{sp['name']}")
                runde["einsaetze"][sp["name"]] = einsatz

            st.subheader("Plätze")
            for sp in st.session_state.spieler:
                platz = st.number_input(f"{sp['name']} Platz (Runde {idx+1})",
                                        min_value=1, step=1,
                                        value=runde["plaetze"].get(sp["name"], 1),
                                        key=f"platz_{idx}_{sp['name']}")
                runde["plaetze"][sp["name"]] = platz

            if st.button(f"Runde {idx+1} speichern", key=f"save_runde_{idx}"):
                runde["saved"] = True
                st.session_state.runde_aktualisiert = True

    # Punkte neu berechnen nur wenn gespeichert wurde
    if st.session_state.runde_aktualisiert:
        for sp in st.session_state.spieler:
            sp["einsaetze"] = []
            sp["plaetze"] = []
            sp["gewinne"] = []

        for runde in st.session_state.runden:
            for sp in st.session_state.spieler:
                einsatz = runde["einsaetze"].get(sp["name"], 0)
                platz = runde["plaetze"].get(sp["name"], 1)
                multiplikator = st.session_state.multiplikatoren[platz - 1] if 0 < platz <= len(st.session_state.multiplikatoren) else 0
                gewinn = int(einsatz * multiplikator)
                sp["einsaetze"].append(einsatz)
                sp["plaetze"].append(platz)
                sp["gewinne"].append(gewinn)

        for sp in st.session_state.spieler:
            sp["punkte"] = 20 + sum(g - e for g, e in zip(sp["gewinne"], sp["einsaetze"]))

        st.session_state.runde_aktualisiert = False

    # Spielstand Tabelle (sortiert Punkte absteigend)
    st.header("Spielstand")
    daten = []
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
        # Letzte 3 Runden in umgekehrter Reihenfolge anzeigen
        for i in range(len(st.session_state.runden) - 1, max(-1, len(st.session_state.runden) - 4), -1):
            if i < len(sp["einsaetze"]):
                zeile[f"Runde {i+1}"] = f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{int(sp['gewinne'][i])}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
