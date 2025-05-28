
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import uuid

def get_firestore_client():
    # Prüfen, ob eine Firebase-App bereits initialisiert wurde
    if not firebase_admin._apps:
        # Aus st.secrets laden (secrets.toml oder Streamlit Cloud)
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    # Firestore-Client zurückgeben
    return firestore.client()

db = get_firestore_client()

    ## Vor der Berechnung: Punktestand pro Spieler vor jeder Runde speichern
    zwischenpunkte = {sp["name"]: 20.0 for sp in st.session_state.spieler}
    bonus_empfaenger_pro_runde = []

    # Leere die Einträge
    for sp in st.session_state.spieler:
        sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []

    # Berechnung pro Runde
    for runde_idx, runde in enumerate(st.session_state.runden):
        # Bestimme Bonus-Empfänger (ab Runde 2)
        if runde_idx == 0:
            bonus_empfaenger = []
        else:
            min_punkte = min(zwischenpunkte.values())
            bonus_empfaenger = [name for name, punkte in zwischenpunkte.items() if punkte == min_punkte]
        bonus_empfaenger_pro_runde.append(bonus_empfaenger)

        # Berechne Gewinne
        for sp in st.session_state.spieler:
            name = sp["name"]
            einsatz = runde["einsaetze"].get(name, 0)
            platz = runde["plaetze"].get(name, 1)
            multiplikator = st.session_state.multiplikatoren[platz - 1] if platz - 1 < len(st.session_state.multiplikatoren) else 0

            gewinn = einsatz * multiplikator
            if name in bonus_empfaenger and multiplikator < 0:
                gewinn = 0  # Bonus für alle Letzten

            sp["einsaetze"].append(einsatz)
            sp["plaetze"].append(platz)
            sp["gewinne"].append(float(gewinn))

        # Update Zwischenpunkte für nächste Runde
        for sp in st.session_state.spieler:
            zwischenpunkte[sp["name"]] += sp["gewinne"][-1]

    # Aktualisiere Gesamtpunkte
    for sp in st.session_state.spieler:
        sp["punkte"] = 20.0 + sum(sp["gewinne"])

    # Spielstand
    st.header("Spielstand")
    daten = []
    # Spieler mit Bonus pro Runde ermitteln
    bonus_empfaenger_pro_runde = []
    punkte_zwischen_runden = [ {sp["name"]: 20.0} for sp in st.session_state.spieler ]  # Startpunkte

    zwischenpunkte = {sp["name"]: 20.0 for sp in st.session_state.spieler}
    for runde_idx, runde in enumerate(st.session_state.runden):
        if runde_idx == 0:
            # In der ersten Runde kein Bonus
            bonus_empfaenger_pro_runde.append(None)
        else:
            min_punkte = min(zwischenpunkte.values())
            letzte_spieler = [name for name, punkte in zwischenpunkte.items() if punkte == min_punkte]
            bonus_empfaenger_pro_runde.append(letzte_spieler)

        # Punktestand für nächste Runde aktualisieren
        for sp in st.session_state.spieler:
            zwischenpunkte[sp["name"]] += sp["gewinne"][runde_idx]
            
    # Anzeige
    for sp in sorted(st.session_state.spieler, key=lambda x: -x["punkte"]):
        zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"],1)}
        for i in range(len(st.session_state.runden) - 1, -1, -1):
            runde = st.session_state.runden[i]
            if i < len(sp["einsaetze"]):
                bonus_symbol = "★" if bonus_empfaenger_pro_runde[i] and sp["name"] in bonus_empfaenger_pro_runde[i] else ""
                vorzeichen = "+" if sp['gewinne'][i] > 0 else ""
                zeile[runde["name"]] = (
                    f"E: {int(sp['einsaetze'][i])} | "
                    f"P: {sp['plaetze'][i]} | "
                    f"{vorzeichen}{round(sp['gewinne'][i],1)}{bonus_symbol}"
                )
        daten.append(zeile)

    df = pd.DataFrame(daten)
    st.dataframe(df, use_container_width=True, hide_index=True)


    # AUTOMATISCHES SPEICHERN
    if "spielname" in st.session_state:
        try:
            spiel_daten = {
                "spieler": st.session_state.spieler,
                "multiplikatoren": st.session_state.multiplikatoren,
                "runden": st.session_state.runden,
                "zeitstempel": firestore.SERVER_TIMESTAMP
            }
            db.collection("spiele").document(st.session_state.spielname).set(spiel_daten)
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")            

# Verlaufsgrafik
st.subheader("📈 Punkteverlauf")
df_chart = pd.DataFrame(punkteverlauf)

# Nur Runden bis zur vorletzten Runde behalten
max_runden_index = len(runden) - 2  # da 0-basiert, -2 = vorletzte Runde
# Runde ist String wie "1: XYZ", wir filtern nach der Rundenzahl vor dem Doppelpunkt

df_chart = df_chart[df_chart["Runde"].apply(
    lambda r: int(r.split(":")[0]) <= max_runden_index + 1  # +1 da Runde 1-basiert
)]

chart = alt.Chart(df_chart).mark_line(point=True).encode(
    x="Runde",
    y=alt.Y("Punkte", scale=alt.Scale(zero=False)),
    color="Spieler",
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)
aktuelle_runde_index = len(runden) - 1  # Index der letzten Runde (0-basiert)
aktuelle_runde_name = f"{len(runden)}: {runden[-1]['name']}"

