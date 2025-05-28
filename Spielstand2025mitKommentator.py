import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import random
import altair as alt
from datetime import datetime

# Firestore-Verbindung

def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

# Spielname festlegen (fest eingebaut)
savegame_name = "Vatertagsspiele 2025"
spiel_ref = db.collection("spiele").document(savegame_name)
spiel_doc = spiel_ref.get()

if not spiel_doc.exists:
    st.error("Spiel nicht gefunden.")
    st.stop()

daten = spiel_doc.to_dict()
spieler = daten["spieler"]
multiplikatoren = daten["multiplikatoren"]
runden = daten["runden"]
kommentare = daten.get("kommentare", [])

# Punkte neu berechnen (wie im Hauptspiel)
punkteverlauf = []

for sp in spieler:
    sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
    sp["punkte"] = 20.0

for i, runde in enumerate(runden):
    punkte_vor_runde = {sp["name"]: sp["punkte"] for sp in spieler}
    letzter_spieler = min(punkte_vor_runde, key=punkte_vor_runde.get)
    for sp in spieler:
        einsatz = runde["einsaetze"].get(sp["name"], 0)
        platz = runde["plaetze"].get(sp["name"], 1)
        multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0
        if sp["name"] == letzter_spieler:
            multiplikator *= 2
        gewinn = float(einsatz * multiplikator)
        sp["einsaetze"].append(einsatz)
        sp["plaetze"].append(platz)
        sp["gewinne"].append(gewinn)
        sp["punkte"] += gewinn
        punkteverlauf.append({"Runde": f"{i+1}: {runde['name']}", "Spieler": sp["name"], "Punkte": sp["punkte"]})

for sp in spieler:
    sp["punkte"] = round(sp["punkte"], 2)

# Bonus pro Runde berechnen
bonus_empfaenger_pro_runde = []
zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}
for runde_idx, runde in enumerate(runden):
    if runde_idx == 0:
        bonus_empfaenger_pro_runde.append(None)
    else:
        letzter_spieler = min(zwischenpunkte, key=zwischenpunkte.get)
        bonus_empfaenger_pro_runde.append(letzter_spieler)
    for sp in spieler:
        zwischenpunkte[sp["name"]] += sp["gewinne"][runde_idx]

# Anzeige des Spielstands
st.set_page_config(page_title="Spielstand 2025", layout="wide")
st.title("🎲 Spielstand:")
st.subheader(f"Spiel: {savegame_name}")

anzeige = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
    for i in range(len(runden) - 1, -1, -1):
        runde = runden[i]
        if i < len(sp["einsaetze"]):
            bonus_symbol = "*" if sp["name"] == bonus_empfaenger_pro_runde[i] else ""
            zeile[runde["name"]] = (
                f"E: {int(sp['einsaetze'][i])} | P: {sp['plaetze'][i]} | +{round(sp['gewinne'][i], 1)}{bonus_symbol}"
            )
    anzeige.append(zeile)

df = pd.DataFrame(anzeige)
st.dataframe(df, use_container_width=True, hide_index=True)

# Kommentator-Funktion
kommentar_templates = {
    "fuehrung": [
        "🏆 {name} führt das Feld an – Respekt!",
        "🚀 {name} ist aktuell nicht zu stoppen!",
        "👑 {name} thront an der Spitze – noch...",
        "💪 {name} zeigt allen, wo der Hammer hängt!",
        "😎 {name} führt – und lässt's aussehen wie ein Spaziergang im Park.",
        "🎖️ {name} macht den anderen mal eben den Highscore kaputt.",
        "🦁 {name} brüllt von ganz oben – keine Gnade!",
        "📈 {name} kennt offenbar nur eine Richtung: aufwärts!"


    ],
    "letzter": [
        "🥴 {name} kämpft noch... irgendwie.",
        "🐢 {name} kommt wohl mit Anlauf von hinten!",
        "🪫 {name} scheint im Energiesparmodus zu spielen.",
        "📉 {name} braucht einen Motivationsschub!",
        "💤 {name} scheint das Spiel meditativ anzugehen.",
        "🍀 {name} hat leider nur das Kleeblatt vergessen.",
        "📉 {name} sucht vermutlich noch den Turbo-Knopf.",
        "🧱 {name} baut gerade am Fundament... ganz unten."

    ],
    "bonus": [
        "🎁 Rubber-Banding für {name}! Und was macht {name} draus?",
        "🔥 {name} mit Rubber-Banding – jetzt kann's krachen!",
        "🎲 {name} spielt mit Rubber-Banding – Glück oder Können?",
        "✨ {name} konnte nichts verlieren – was macht er draus?",
        "🎉 {name} bekommt Hilfe – aber nutzt er sie auch sinnvoll? 🤔",
        "🧨 Rubber-Banding für {name} – gleich knallt's hoffentlich!",
        "💼 {name} hat's irgendwie geschafft abzustauben.",
        "👀 Alle Augen auf {name} – mit Rubber-Banding gehts Bergauf!"

    ],
    "rundegewinner": [
        "💸 {name} sahnt richtig ab mit +{gewinn} Punkten!",
        "🎯 {name} hat die Runde gerockt!",
        "🥳 Runde geht klar an {name} – das war stark!",
        "💥 Boom! {name} hat zugeschlagen: +{gewinn} Punkte!",
        "🎆 {name} hat die Runde mit Stil gewonnen – Applaus!",
        "🏹 {name} hat genau ins Schwarze getroffen!",
        "💰 +{gewinn} Punkte? {name} geht heute shoppen!",
        "🧙‍♂️ {name} zaubert sich an die Spitze der Runde!"
    ]
}

def zufalls_kommentar(kategorie, **kwargs):
    vorlagen = kommentar_templates.get(kategorie, [])
    if vorlagen:
        return random.choice(vorlagen).format(**kwargs)
    return None

# Kommentare aktualisieren, falls neue Runde
anzahl_kommentare = len(kommentare)
anzahl_runden = len(runden)

if anzahl_runden > anzahl_kommentare:
    neue_kommentare = []
    for i in range(anzahl_kommentare, anzahl_runden):
        ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        fuehrender = max(spieler, key=lambda x: x["punkte"])
        letzter = min(spieler, key=lambda x: x["punkte"])
        runde_beste = max(spieler, key=lambda x: x["gewinne"][i])
        bonus_empfaenger = bonus_empfaenger_pro_runde[i]
        neue_kommentare.extend([
            {"zeit": ts, "text": zufalls_kommentar("fuehrung", name=fuehrender["name"])},
            {"zeit": ts, "text": zufalls_kommentar("letzter", name=letzter["name"])},
            {"zeit": ts, "text": zufalls_kommentar("rundegewinner", name=runde_beste["name"], gewinn=round(runde_beste["gewinne"][i], 1))},
        ])
        if bonus_empfaenger:
            neue_kommentare.append({"zeit": ts, "text": zufalls_kommentar("bonus", name=bonus_empfaenger)})
    kommentare.extend(neue_kommentare)
    spiel_ref.update({"kommentare": kommentare})

# Anzeige aller Kommentare (neueste zuerst)
st.header("🎙️ Kommentator:")
for eintrag in reversed(kommentare):
    st.markdown(f"**{eintrag['zeit']}** – {eintrag['text']}")

# Punkteverlaufsgrafik
st.subheader("📈 Punkteentwicklung pro Spieler")
df_verlauf = pd.DataFrame(punkteverlauf)
chart = alt.Chart(df_verlauf).mark_line(point=True).encode(
    x="Runde",
    y=alt.Y("Punkte", scale=alt.Scale(zero=False)),
    color="Spieler",
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)
st.altair_chart(chart, use_container_width=True)
