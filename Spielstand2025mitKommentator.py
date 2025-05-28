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
            multiplikator *= 1
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

# Refresh Button
if st.button("🔄 Seite aktualisieren"):
    st.experimental_rerun()

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
        "💪 {name} zeigt allen, wo der Hammer hängt!"
    ],
    "letzter": [
        "🥴 {name} kämpft noch... irgendwie.",
        "🐢 {name} kommt wohl mit Anlauf von hinten!",
        "🪫 {name} scheint im Energiesparmodus zu spielen.",
        "📉 {name} braucht einen Motivationsschub!"
    ],
    "bonus": [
        "🎁 Bonus für {name}! Und was macht {name} draus?",
        "🔥 {name} mit dem Bonus – jetzt kann's krachen!",
        "🎲 {name} bekommt extra Punkte – Glück oder Können?",
        "✨ Bonusregen für {name} – viel Spaß!"
    ],
    "rundegewinner": [
        "💸 {name} sahnt richtig ab mit +{gewinn} Punkten!",
        "🎯 {name} hat die Runde gerockt!",
        "🥳 Runde geht klar an {name} – das war stark!",
        "💥 Boom! {name} hat zugeschlagen: +{gewinn} Punkte!"
    ]
}

def zufalls_kommentar(kategorie, **kwargs):
    vorlagen = kommentar_templates.get(kategorie, [])
    if vorlagen:
        return random.choice(vorlagen).format(**kwargs)
    return None

def generiere_kommentare(spieler, runden, multiplikatoren, bonus_empfaenger_pro_runde, kommentare, spiel_ref):
    """
    Generiert Kommentare basierend auf dem Zustand nach der letzten abgeschlossenen Runde.
    Es werden keine Kommentare generiert, wenn keine Runde abgeschlossen ist oder nur 1 Runde existiert (laufende Runde).
    """
    anzahl_runden = len(runden)
    # Kommentare nur generieren, wenn mindestens 2 Runden existieren (also mindestens 1 abgeschlossene)
    if anzahl_runden < 2:
        return kommentare  # nichts zu tun

    letzte_abgeschlossene_runde_idx = anzahl_runden - 2  # die letzte komplett abgeschlossene Runde

    # Prüfen, ob für diese Runde schon Kommentare existieren, um doppelte zu vermeiden
    schon_vorhanden = any(k.get("runde") == letzte_abgeschlossene_runde_idx for k in kommentare)
    if schon_vorhanden:
        return kommentare

    # Punkte nach der letzten abgeschlossenen Runde berechnen
    punkte_nach_runde = {}
    for sp in spieler:
        punkte_nach_runde[sp["name"]] = 20.0 + sum(sp["gewinne"][:letzte_abgeschlossene_runde_idx + 1])

    # Führender und Letzter nach letzter abgeschlossener Runde
    fuehrender_name = max(punkte_nach_runde, key=punkte_nach_runde.get)
    letzter_name = min(punkte_nach_runde, key=punkte_nach_runde.get)

    # Gewinner der letzten Runde (mit höchstem Gewinn in dieser Runde)
    gewinner_runde = max(spieler, key=lambda x: x["gewinne"][letzte_abgeschlossene_runde_idx])
    gewinn_betrag = round(gewinner_runde["gewinne"][letzte_abgeschlossene_runde_idx], 1)

    # Bonus-Empfänger der letzten Runde
    bonus_empfaenger = None
    if letzte_abgeschlossene_runde_idx < len(bonus_empfaenger_pro_runde):
        bonus_empfaenger = bonus_empfaenger_pro_runde[letzte_abgeschlossene_runde_idx]

    ts = datetime.now().isoformat()

    neue_kommentare = []
    neue_kommentare.append({
        "zeit": ts,
        "text": zufalls_kommentar("rundegewinner", name=gewinner_runde["name"], gewinn=gewinn_betrag),
        "runde": letzte_abgeschlossene_runde_idx
    })
    if bonus_empfaenger and isinstance(bonus_empfaenger, str):
        neue_kommentare.append({
            "zeit": ts,
            "text": zufalls_kommentar("bonus", name=bonus_empfaenger),
            "runde": letzte_abgeschlossene_runde_idx
        })
    neue_kommentare.append({
        "zeit": ts,
        "text": zufalls_kommentar("fuehrung", name=fuehrender_name),
        "runde": letzte_abgeschlossene_runde_idx
    })
    neue_kommentare.append({
        "zeit": ts,
        "text": zufalls_kommentar("letzter", name=letzter_name),
        "runde": letzte_abgeschlossene_runde_idx
    })

    kommentare.extend(neue_kommentare)
    spiel_ref.update({"kommentare": kommentare})

    return kommentare

# Nachdem die neue Runde hinzugefügt wurde und die Daten aktualisiert sind:
kommentare = generiere_kommentare(spieler, runden, multiplikatoren, bonus_empfaenger_pro_runde, kommentare, spiel_ref)


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
