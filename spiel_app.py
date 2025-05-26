import streamlit as st
import pandas as pd

st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Spielverwaltung mit editierbaren Runden")

# Initialisierung Session State
if "spieler" not in st.session_state:
    st.session_state.spieler = []
if "multiplikatoren" not in st.session_state:
    st.session_state.multiplikatoren = []
if "runden" not in st.session_state:
    # Liste von dicts: {name:str, einsaetze: dict Spieler->int, plaetze: dict Spieler->int}
    st.session_state.runden = []
if "spiel_started" not in st.session_state:
    st.session_state.spiel_started = False

# --- Spiel Setup ---
if not st.session_state.spiel_started:
    st.header("Spiel Setup")
    spieler_input = st.text_area("Spielernamen (je eine pro Zeile):")
    multiplikator_input = st.text_input("Multiplikatoren pro Platz (z.B. 3,2,1):")

    spiel_starten = st.button("Spiel starten")
    if spiel_starten:
        spieler = [n.strip() for n in spieler_input.strip().split("\n") if n.strip()]
        try:
            multiplikatoren = [float(x.strip()) for x in multiplikator_input.split(",") if x.strip()]
        except:
            st.error("Multiplikatoren bitte als Komma-getrennte Zahlen eingeben (z.B. 3,2,1)")
            multiplikatoren = []
        if spieler and multiplikatoren:
            st.session_state.spieler = spieler
            st.session_state.multiplikatoren = multiplikatoren
            st.session_state.spiel_started = True
            # Direkt erste Runde anlegen
            st.session_state.runden = [{
                "name": "Runde 1",
                "einsaetze": {sp: 0 for sp in spieler},
                "plaetze": {sp: 1 for sp in spieler},
            }]
        else:
            st.warning("Bitte gültige Spieler- und Multiplikatoreneingaben machen.")

# --- Spiel läuft ---
else:
    st.header("Rundenverwaltung")

    if st.button("Neue Runde starten"):
        neue_num = len(st.session_state.runden) + 1
        st.session_state.runden.append({
            "name": f"Runde {neue_num}",
            "einsaetze": {sp: 0 for sp in st.session_state.spieler},
            "plaetze": {sp: 1 for sp in st.session_state.spieler},
        })

    # Runden editieren (Rundennamen, Einsätze, Plätze)
    for idx, runde in enumerate(st.session_state.runden):
        with st.expander(f"{runde['name']} (Runde {idx+1})", expanded=True):
            # Name editierbar
            neuer_name = st.text_input(f"Name Runde {idx+1}", value=runde["name"], key=f"rundename_{idx}")
            st.session_state.runden[idx]["name"] = neuer_name

            st.subheader("Einsätze pro Spieler")
            for sp in st.session_state.spieler:
                einsatz = st.number_input(f"{sp} Einsatz (Runde {idx+1})", min_value=0, step=1,
                                         value=runde["einsaetze"].get(sp, 0), key=f"einsatz_{idx}_{sp}")
                st.session_state.runden[idx]["einsaetze"][sp] = einsatz

            st.subheader("Platzierung pro Spieler")
            for sp in st.session_state.spieler:
                platz = st.number_input(f"{sp} Platz (Runde {idx+1})", min_value=1, step=1,
                                        value=runde["plaetze"].get(sp, 1), key=f"platz_{idx}_{sp}")
                st.session_state.runden[idx]["plaetze"][sp] = platz

    # Punkte berechnen
    spieler_data = []
    for sp in st.session_state.spieler:
        punkte = 20
        einsaetze_list = []
        plaetze_list = []
        gewinne_list = []
        for runde in st.session_state.runden:
            einsatz = runde["einsaetze"].get(sp, 0)
            platz = runde["plaetze"].get(sp, 1)
            multiplikator = 0
            if 0 < platz <= len(st.session_state.multiplikatoren):
                multiplikator = st.session_state.multiplikatoren[platz - 1]
            gewinn = int(einsatz * multiplikator)
            punkte += gewinn - einsatz
            einsaetze_list.append(einsatz)
            plaetze_list.append(platz)
            gewinne_list.append(gewinn)
        spieler_data.append({
            "Spieler": sp,
            "Punkte": punkte,
            "Einsaetze": einsaetze_list,
            "Plaetze": plaetze_list,
            "Gewinne": gewinne_list,
        })

    # Tabelle anzeigen mit letzten 3 Runden (umgekehrte Reihenfolge)
    st.header("Spielstand (letzte 3 Runden)")
    daten = []
    letzte_runden = st.session_state.runden[-3:] if len(st.session_state.runden) >= 3 else st.session_state.runden
    runden_indices = range(len(st.session_state.runden) - len(letzte_runden), len(st.session_state.runden))
    for sp in sorted(spieler_data, key=lambda x: -x["Punkte"]):
        zeile = {"Spieler": sp["Spieler"], "Punkte": sp["Punkte"]}
        for i, r_idx in enumerate(runden_indices):
            zeile[f"{st.session_state.runden[r_idx]['name']}"] = (
                f"E: {sp['Einsaetze'][r_idx]} | P: {sp['Plaetze'][r_idx]} | +{sp['Gewinne'][r_idx]}"
            )
        daten.append(zeile)
    df = pd.DataFrame(daten).fillna("")
    st.dataframe(df, use_container_width=True)
