Spielverwaltung als mehrnutzerfähige Streamlit App mit Session- und Zustandsspeicherung

import streamlit as st import pandas as pd import uuid

st.set_page_config(page_title="Mehrnutzer Spielverwaltung", layout="wide") st.title("Mehrnutzer Spielverwaltung")

Initialisierung von Zustand

if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())

if "spieler" not in st.session_state: st.session_state.spieler = [] if "multiplikatoren" not in st.session_state: st.session_state.multiplikatoren = [] if "runden" not in st.session_state: st.session_state.runden = [] if "spiel_started" not in st.session_state: st.session_state.spiel_started = False

SPIEL START

if not st.session_state.spiel_started: st.header("Spiel Setup") spieler_input = st.text_area("Spieler (ein Name pro Zeile)") multi_input = st.text_input("Multiplikatoren pro Platz (z. B. 3,2,1)")

if st.button("Spiel starten"):
    st.session_state.spieler = [
        {"name": name.strip(), "punkte": 20, "einsaetze": [], "plaetze": [], "gewinne": []}
        for name in spieler_input.strip().split("\n") if name.strip()
    ]
    st.session_state.multiplikatoren = [float(x.strip()) for x in multi_input.split(",") if x.strip()]
    st.session_state.spiel_started = True
    st.experimental_rerun()

SPIELBEREICH

else: st.header("Rundenverwaltung") neue_runde = st.button("Neue Runde starten")

if neue_runde:
    st.session_state.runden.append({"name": f"Runde {len(st.session_state.runden)+1}", "einsaetze": {}, "plaetze": {}})

for runden_index, runde in enumerate(st.session_state.runden[::-1]):
    echte_index = len(st.session_state.runden) - 1 - runden_index
    with st.expander(f"{runde['name']}", expanded=(runden_index == 0)):
        runde["name"] = st.text_input(f"Name Runde {echte_index+1}", value=runde["name"], key=f"rundenname_{echte_index}")

        st.markdown("**Einsätze**")
        for i, sp in enumerate(st.session_state.spieler):
            key = f"einsatz_{echte_index}_{i}"
            val = runde["einsaetze"].get(sp["name"], 0)
            runde["einsaetze"][sp["name"]] = st.number_input(f"{sp['name']}: Einsatz", min_value=0.0, value=val, key=key)

        if st.button(f"Speichern & Weiter zu Platzierungen - Runde {echte_index+1}", key=f"weiter_{echte_index}"):
            st.experimental_rerun()

        st.markdown("**Platzierungen**")
        for i, sp in enumerate(st.session_state.spieler):
            key = f"platz_{echte_index}_{i}"
            val = runde["plaetze"].get(sp["name"], 1)
            runde["plaetze"][sp["name"]] = st.number_input(f"{sp['name']}: Platz", min_value=1, value=val, step=1, key=key)

        # Berechnung der Punkte
        for sp in st.session_state.spieler:
            einsatz = runde["einsaetze"].get(sp["name"], 0)
            platz = runde["plaetze"].get(sp["name"], 1)
            multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0
            gewinn = einsatz * multiplikator
            # Speichern in Spielerobjekt
            if len(sp["einsaetze"]) <= echte_index:
                sp["einsaetze"].append(einsatz)
                sp["plaetze"].append(platz)
                sp["gewinne"].append(gewinn)
            else:
                sp["einsaetze"][echte_index] = einsatz
                sp["plaetze"][echte_index] = platz
                sp["gewinne"][echte_index] = gewinn

# Punkte aktualisieren
for sp in st.session_state.spieler:
    sp["punkte"] = 20 + sum([g - e for g, e in zip(sp["gewinne"], sp["einsaetze"])])

st.header("Spielstand")
df = pd.DataFrame([
    {
        "Spieler": sp["name"],
        "Punkte": sp["punkte"],
        **{f"R{ri+1}": f"E: {sp['einsaetze'][ri]} | P: {sp['plaetze'][ri]} | +{sp['gewinne'][ri]:.1f}" for ri in range(len(st.session_state.runden))}
    } for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"])
])
st.dataframe(df, use_container_width=True)

