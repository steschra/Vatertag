import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from urllib.parse import parse_qs

# Firebase initialisieren
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Spiel-ID aus URL oder Eingabe
params = st.query_params.to_dict()
spiel_id = params.get("spiel") or st.text_input("Spielname eingeben:", value="mein-spiel")
if not spiel_id:
    st.stop()

spiel_ref = db.collection("spiele").document(spiel_id)
doc = spiel_ref.get()
if not doc.exists:
    spiel_data = {
        "spieler": [],
        "runden": [],
        "multiplikatoren": [3, 2, 1]
    }
    spiel_ref.set(spiel_data)
else:
    spiel_data = doc.to_dict()

spieler = spiel_data["spieler"]
runden = spiel_data["runden"]
multiplikatoren = spiel_data.get("multiplikatoren", [3, 2, 1])

st.title(f"Spiel: {spiel_id}")

# Setup-Bereich (nur wenn noch keine Spieler vorhanden)
if not spieler:
    st.header("Spiel Setup")
    spieler_input = st.text_area("Spielernamen (einer pro Zeile):")
    multiplikator_input = st.text_input("Multiplikatoren pro Platz (z. B. 3,2,1):")
    if st.button("Spiel starten"):
        neue_spieler = [name.strip() for name in spieler_input.split("\n") if name.strip()]
        multiplikatoren = [float(x.strip()) for x in multiplikator_input.split(",") if x.strip()]
        spiel_data.update({
            "spieler": [{"name": name, "punkte": 20} for name in neue_spieler],
            "multiplikatoren": multiplikatoren
        })
        spiel_ref.set(spiel_data)
        st.experimental_rerun()
    st.stop()

# Neue Runde erstellen
st.subheader("Neue Runde starten")
runde_name = st.text_input("Rundenname eingeben")
if st.button("Neue Runde anlegen") and runde_name:
    neue_runde = {
        "name": runde_name,
        "einsaetze": {sp["name"]: 0 for sp in spieler},
        "plaetze": {sp["name"]: 1 for sp in spieler}
    }
    runden.append(neue_runde)
    spiel_data["runden"] = runden
    spiel_ref.update({"runden": runden})
    st.experimental_rerun()

# Runden anzeigen und bearbeiten
st.header("Runden bearbeiten")
aktualisiert = False
for r_idx in range(len(runden)-1, -1, -1):
    runde = runden[r_idx]
    with st.expander(f"{runde['name']}", expanded=(r_idx == len(runden)-1)):
        new_name = st.text_input(f"Rundenname", value=runde["name"], key=f"runde_name_{r_idx}")
        if new_name != runde["name"]:
            runde["name"] = new_name
            aktualisiert = True

        for sp in spieler:
            name = sp["name"]
            runde["einsaetze"][name] = st.number_input(
                f"{name} Einsatz", min_value=0, step=1,
                value=runde["einsaetze"].get(name, 0), key=f"einsatz_{r_idx}_{name}"
            )
            runde["plaetze"][name] = st.number_input(
                f"{name} Platz", min_value=1, step=1,
                value=runde["plaetze"].get(name, 1), key=f"platz_{r_idx}_{name}"
            )
        if st.button("Speichern", key=f"save_runde_{r_idx}"):
            spiel_ref.update({"runden": runden})
            st.experimental_rerun()

# Punkte berechnen
for sp in spieler:
    sp["punkte"] = 20
    for runde in runden:
        einsatz = runde["einsaetze"].get(sp["name"], 0)
        platz = runde["plaetze"].get(sp["name"], 1)
        multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0
        gewinn = int(einsatz * multiplikator)
        sp["punkte"] += gewinn

spiel_data["spieler"] = spieler
spiel_ref.update({"spieler": spieler})

# Tabelle anzeigen
st.header("Spielstand")
data = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": int(sp["punkte"])}
    for i in range(len(runden)-1, -1, -1):
        r = runden[i]
        zeile[r["name"]] = f"E: {r['einsaetze'][sp['name']]} | P: {r['plaetze'][sp['name']]}"
    data.append(zeile)

st.dataframe(data, use_container_width=True)
