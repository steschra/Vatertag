import streamlit as st
import pandas as pd

st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Spielverwaltung mit editierbaren Runden")

# Session State initialisieren
if "spieler" not in st.session_state:
    st.session_state.spieler = []
if "multiplikatoren" not in st.session_state:
    st.session_state.multiplikatoren = []
if "runden" not in st.session_state:
    st.session_state.runden = []
if "spiel_started" not in st.session_state:
    st.session_state.spiel_started = False

# --- Spiel Setup ---
if not st.session_state.spiel_started:
    st.header("Spiel Setup")

    spieler_input = st.text_area("Spielernamen (je eine pro Zeile):")
    multiplikator_input = st.text_input("Multiplikatoren pro Platz (z.B. 3,2,1):")

    if st.button("Spiel starten"):
        spieler = [n.strip() for n in spieler_input.strip().split("\n") if n.strip()]
        try:
            multiplikatoren = [float(x.strip()) for x in multiplikator_input.split(",") if x.strip()]
        except:
            st.error("Bitte Multiplikatoren als Komma-getrennte Zahlen eingeben (z.B. 3,2,1).")
            multiplikatoren = []

        if spieler and multiplikatoren:
            st.session_state.spieler = spieler
            st.session_state.multiplikatoren = multiplikatoren
            st.session_state.spiel_started = True
            # Erste Runde anlegen
            st.session_state.runden = [{
                "name": "Runde 1",
                "einsaetze": {sp: 0 for sp in spieler},
                "plaetze": {sp: 1 for sp in spieler},
            }]
        else:
            st.warning("Bitte gültige Spielernamen und Multiplikatoren eingeben.")

# --- Spiel läuft ---
else:
    st.header("Rundenverwaltung")

    # Runden editieren (alle Runden ausgeklappt)
    for idx, runde in enumerate(st.session_state.runden):
        with st.expander(f"Runde {idx + 1}: {runde['name']}", expanded=False):
            # Rundennamen editierbar
            neuer_name = st.text_input(f"Name Runde {idx + 1}", value=runde["name"], key=f"rundename_{idx}")
            st.session_state.runden[idx]["name"] = neuer_name

            st.markdown("**Einsätze pro Spieler**")
            for sp in st.session_state.spieler:
                einsatz = st.number_input(f"{sp} Einsatz (Runde {idx + 1})", min_value=0, step=1,
                                         value=runde["einsaetze"].get(sp, 0), key=f"einsatz_{idx}_{sp}")
                st.session_state.runden[idx]["einsaetze"][sp] = einsatz

            st.markdown("**Platzierung pro Spieler**")
            for sp in st.session_state.spieler:
                platz = st.number_input(f"{sp} Platz (Runde {idx + 1})", min_value=1, step=1,
                                        value=runde["plaetze"].get(sp, 1), key=f"platz_{idx}_{sp}")
                st.session_state.runden[idx]["plaetze"][sp] = platz

    st.markdown("---")
    # Button zum Starten neuer Runde (zwischen Runden und Tabelle)
    if st.button("Neue Runde starten"):
        neue_rundennummer = len(st.session_state.runden) + 1
        st.session_state.runden.append({
            "name": f"Runde {neue_rundennummer}",
            "einsaetze": {sp: 0 for sp in st.session_state.spieler},
            "plaetze": {sp: 1 for sp in st.session_state.spieler},
        })

    st.markdown("---")
    st.header("Spielstand (letzte 3 Runden, neueste zuerst)")

    # Punkte berechnen pro Spieler
    spieler_data = []
    for sp in st.session_state.spieler:
        punkte = 20
        einsaetze = []
        plaetze = []
        gewinne = []
        for runde in st.session_state.runden:
            einsatz = runde["einsaetze"].get(sp, 0)
            platz = runde["plaetze"].get(sp, 1)
            multiplikator = 0
            if 1 <= platz <= len(st.session_state.multiplikatoren):
                multiplikator = st.session_state.multiplikatoren[platz - 1]
            gewinn = int(einsatz * multiplikator)
            punkte += gewinn - einsatz
            einsaetze.append(einsatz)
            plaetze.append(platz)
            gewinne.append(gewinn)
        spieler_data.append({
            "Spieler": sp,
            "Punkte": punkte,
            "Einsaetze": einsaetze,
            "Plaetze": plaetze,
            "Gewinne": gewinne,
        })

    # Die letzten 3 Runden umgekehrt (neueste zuerst)
    runden_letzte = st.session_state.runden[-3:]
    runden_letzte = list(reversed(runden_letzte))
    runden_indices = list(range(len(st.session_state.runden) - len(runden_letzte), len(st.session_state.runden)))
    runden_indices.reverse()

    # Tabelle bauen
    tabellen_daten = []
    # Sortiert nach Punkte absteigend
    spieler_data_sort = sorted(spieler_data, key=lambda x: -x["Punkte"])
    for sp_data in spieler_data_sort:
        zeile = {"Spieler": sp_data["Spieler"], "Punkte": sp_data["Punkte"]}
        for i, r_idx in enumerate(runden_indices):
            name_runde = st.session_state.runden[r_idx]["name"]
            zeile[f"{name_runde}"] = f"E: {sp_data['Einsaetze'][r_idx]} | P: {sp_data['Plaetze'][r_idx]} | +{sp_data['Gewinne'][r_idx]}"
        tabellen_daten.append(zeile)

    df = pd.DataFrame(tabellen_daten).fillna("")
    st.dataframe(df, use_container_width=True)
