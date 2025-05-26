import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Firebase initialisieren (nur einmal)
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Spielverwaltung", layout="wide")
st.title("Spielverwaltung mit Mehrbenutzer-Support")

# --- SPIEL AUSWAHL ODER NEU ERSTELLEN ---

spiele_ref = db.collection("spiele")
alle_spiele = spiele_ref.stream()
spiel_liste = [doc.id for doc in alle_spiele]

st.header("Spiel auswählen oder neu anlegen")

wahl = st.selectbox("Existierendes Spiel wählen", options=["-- Neues Spiel erstellen --"] + spiel_liste)

if wahl == "-- Neues Spiel erstellen --":
    neuer_spielname = st.text_input("Neuen Spielnamen eingeben:")
    if st.button("Neues Spiel anlegen") and neuer_spielname:
        doc_ref = spiele_ref.document(neuer_spielname)
        if doc_ref.get().exists:
            st.warning("Spiel existiert bereits! Bitte anderen Namen wählen.")
        else:
            doc_ref.set({
                "spieler": [],
                "runden": [],
                "multiplikatoren": [3, 2, 1]
            })
            st.success(f"Spiel '{neuer_spielname}' wurde angelegt. Bitte Seite neu laden und auswählen.")
        st.stop()
else:
    spiel_id = wahl
    spiel_ref = spiele_ref.document(spiel_id)

    # --- SPIEL DATEN LADEN ---
    doc = spiel_ref.get()
    if not doc.exists:
        st.error("Spiel nicht gefunden!")
        st.stop()

    spiel_data = doc.to_dict()
    spieler = spiel_data.get("spieler", [])
    multiplikatoren = spiel_data.get("multiplikatoren", [3, 2, 1])
    runden = spiel_data.get("runden", [])

    st.markdown(f"### Aktuelles Spiel: **{spiel_id}**")

    # --- SPIELER UND MULTIPLIKATOREN VERWALTEN ---
    with st.expander("Spieler und Multiplikatoren bearbeiten", expanded=False):
        neue_spieler_text = st.text_area(
            "Spielernamen (einer pro Zeile):",
            value="\n".join(spieler)
        )
        multiplikatoren_text = st.text_input(
            "Multiplikatoren pro Platz (z.B. 3,2,1):",
            value=",".join(str(m) for m in multiplikatoren)
        )
        if st.button("Spielerdaten speichern"):
            spieler = [s.strip() for s in neue_spieler_text.strip().split("\n") if s.strip()]
            try:
                multiplikatoren = [float(x.strip()) for x in multiplikatoren_text.split(",") if x.strip()]
                spiel_ref.update({
                    "spieler": spieler,
                    "multiplikatoren": multiplikatoren
                })
                st.success("Spielerdaten aktualisiert!")
            except Exception as e:
                st.error(f"Fehler bei Multiplikatoren: {e}")
            st.experimental_rerun()

    # --- RUNDE ERSTELLEN ---
    if st.button("Neue Runde hinzufügen"):
        neue_runde = {
            "name": f"Runde {len(runden)+1}",
            "einsaetze": {sp: 0 for sp in spieler},
            "plaetze": {sp: 1 for sp in spieler},
            "saved": True
        }
        runden.append(neue_runde)
        spiel_ref.update({"runden": runden})
        st.experimental_rerun()

    # --- RUNDE BEARBEITEN ---
    for idx, runde in enumerate(runden):
        with st.expander(f"{runde['name']} (Runde {idx+1})", expanded=(idx == len(runden)-1)):
            neuer_name = st.text_input(f"Name der Runde {idx+1}", value=runde["name"], key=f"name_{idx}")
            einsaetze = {}
            plaetze = {}

            st.markdown("**Einsätze eingeben:**")
            for sp in spieler:
                einsatz = st.number_input(f"{sp}: Einsatz", min_value=0, step=1,
                                          value=runde["einsaetze"].get(sp, 0), key=f"einsatz_{idx}_{sp}")
                einsaetze[sp] = einsatz

            st.markdown("**Platzierungen eingeben:**")
            for sp in spieler:
                platz = st.number_input(f"{sp}: Platz", min_value=1, step=1,
                                       value=runde["plaetze"].get(sp, 1), key=f"platz_{idx}_{sp}")
                plaetze[sp] = platz

            if st.button(f"Runde {idx+1} speichern", key=f"save_{idx}"):
                runden[idx]["name"] = neuer_name
                runden[idx]["einsaetze"] = einsaetze
                runden[idx]["plaetze"] = plaetze
                runden[idx]["saved"] = True
                spiel_ref.update({"runden": runden})
                st.success(f"Runde {idx+1} gespeichert!")
                st.experimental_rerun()

    # --- PUNKTE BERECHNEN ---
    punkte = {sp: 20 for sp in spieler}  # Startpunkte

    for runde in runden:
        for sp in spieler:
            einsatz = runde["einsaetze"].get(sp, 0)
            platz = runde["plaetze"].get(sp, 1)
            multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0
            gewinn = einsatz * multiplikator
            # Einsatz wird NICHT abgezogen, nur Gewinn addiert
            punkte[sp] += int(gewinn)

    # --- SPIELSTAND TABELLE ---
    st.header("Spielstand")

    import pandas as pd
    daten = []
    for sp in sorted(spieler, key=lambda x: -punkte.get(x, 0)):
        zeile = {"Spieler": sp, "Punkte": punkte.get(sp, 0)}
        # Zeige max 3 letzte Runden in umgekehrter Reihenfolge
        for i in range(max(0, len(runden)-3), len(runden)):
            r = runden[i]
            e = r["einsaetze"].get(sp, 0)
            p = r["plaetze"].get(sp, 1)
            m = multiplikatoren[p-1] if p-1 < len(multiplikatoren) else 0
            g = int(e * m)
            zeile[f"{r['name']}"] = f"E:{e} | P:{p} | +{g}"
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True)
