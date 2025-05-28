import streamlit as st

# Muss als erstes Streamlit-Kommando stehen!
st.set_page_config(page_title="Spielstand ansehen", layout="wide")

import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import altair as alt

# 🔄 Auto-Refresh alle 15 Sekunden
st_autorefresh(interval=15000, key="refresh_viewer")

# Firestore initialisieren (einmalig)
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.header("📊 Spielstand ansehen")

# Spiel auswählen
spiele_docs = db.collection("spiele").stream()
spielnamen = sorted([doc.id for doc in spiele_docs])
spielname = st.selectbox("Spiel auswählen", spielnamen)

if spielname:
    spiel_doc = db.collection("spiele").document(spielname).get()
    if not spiel_doc.exists:
        st.error("Spiel nicht gefunden.")
        st.stop()

    daten = spiel_doc.to_dict()
    spieler = daten.get("spieler", [])
    multiplikatoren = daten.get("multiplikatoren", [])
    runden = daten.get("runden", [])

    if not spieler or not runden:
        st.info("Spiel hat keine Spieler oder Runden.")
        st.stop()

# Punkte summieren (nur zur Anzeige)
for sp in spieler:
    if "gewinne" not in sp:
        sp["gewinne"] = []
    if "einsaetze" not in sp:
        sp["einsaetze"] = []
    if "plaetze" not in sp:
        sp["plaetze"] = []

    sp["punkte"] = 20.0 + sum(sp["gewinne"])

# Bonus extrahieren aus gespeicherten Runden
bonus_empfaenger_pro_runde = []
for r in runden:
    bonus_empfaenger_pro_runde.append(r.get("bonus_empfaenger", []))

# Tabelle bauen
daten = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
    for i in range(len(runden) - 1, -1, -1):
        runde = runden[i]
        if i < len(sp["einsaetze"]):
            bonus_symbol = "★" if sp["name"] in bonus_empfaenger_pro_runde[i] else ""
            vorzeichen = "+" if sp["gewinne"][i] > 0 else ""
            zeile[runde["name"]] = (
                f"E: {sp['einsaetze'][i]} | P: {sp['plaetze'][i]} | "
                f"{vorzeichen}{round(sp['gewinne'][i], 1)}{bonus_symbol}"
            )
    daten.append(zeile)

df = pd.DataFrame(daten)
st.dataframe(df, use_container_width=True, hide_index=True)

# Punkteverlauf pro Runde berechnen
punkteverlauf_data = []
startpunkte = {sp["name"]: 20.0 for sp in spieler}

for i, runde in enumerate(runden):
    for sp in spieler:
        name = sp["name"]
        punkte_bis_dahin = startpunkte[name] + sum(sp["gewinne"][:i+1]) if i < len(sp["gewinne"]) else startpunkte[name]
        punkteverlauf_data.append({
            "Spieler": name,
            "Runde": runde["name"],
            "Punkte": round(punkte_bis_dahin, 1)
        })

# DataFrame bauen
punkte_df = pd.DataFrame(punkteverlauf_data)

# Runde als sortierte Kategorie behandeln
punkte_df["Runde"] = pd.Categorical(punkte_df["Runde"], categories=[r["name"] for r in runden], ordered=True)

# Bereich für y-Achse: min-max der Punkte
min_punkte = punkte_df["Punkte"].min()
max_punkte = punkte_df["Punkte"].max()

# Chart anzeigen
st.subheader("📈 Punkteverlauf pro Spieler")
chart = alt.Chart(punkte_df).mark_line(point=True).encode(
    x=alt.X("Runde:N", title="Runde"),
    y=alt.Y("Punkte:Q", scale=alt.Scale(domain=[min_punkte, max_punkte]), title="Punkte"),
    color=alt.Color("Spieler:N", legend=alt.Legend(orient="bottom")),
    tooltip=["Spieler", "Runde", "Punkte"]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)

# --- Statistik-Bereich ---
st.subheader("📌 Spielstatistiken")

# 1. Häufigster Rundensieger basierend auf den meisten 1. Plätzen
rundensieger = []
for sp in spieler:
    rundensieger.extend([sp["name"]] * sp["plaetze"].count(1))

if rundensieger:
    sieger_serie = pd.Series(rundensieger)
    haeufigster_sieger = sieger_serie.value_counts().idxmax()
    sieger_anzahl = sieger_serie.value_counts().max()
    st.markdown(f"🏆 **Häufigster Rundensieger (1. Plätze):** {haeufigster_sieger} ({sieger_anzahl}x)")
else:
    st.markdown("🏆 Keine ersten Plätze vergeben.")
    
# 2. Häufigster Bonusempfänger
bonus_alle = [name for bonus in bonus_empfaenger_pro_runde for name in (bonus or [])]
if bonus_alle:
    bonus_serie = pd.Series(bonus_alle)
    haeufigster_bonus = bonus_serie.value_counts().idxmax()
    bonus_anzahl = bonus_serie.value_counts().max()
    st.markdown(f"🌟 **Häufigster Bonusempfänger:** {haeufigster_bonus} ({bonus_anzahl}x)")
else:
    st.markdown("🌟 Keine Bonusempfänger erfasst.")

# 3. Höchster Punktestand über alle Runden
punktentwicklung = {sp["name"]: [20.0] for sp in spieler}  # Startpunkte

for r_idx in range(len(runden)):
    for sp in spieler:
        letzter_punktestand = punktentwicklung[sp["name"]][-1]
        gewinn = sp["gewinne"][r_idx] if r_idx < len(sp["gewinne"]) else 0
        punktentwicklung[sp["name"]].append(letzter_punktestand + gewinn)

# Maximalwert suchen
max_punkte = -float("inf")
max_spieler = ""
runde_nummer = -1

for name, punkte_liste in punktentwicklung.items():
    for idx, wert in enumerate(punkte_liste):
        if wert > max_punkte:
            max_punkte = wert
            max_spieler = name
            runde_nummer = idx  # idx == 0 ist Startwert

st.markdown(f"📈 **Höchster Punktestand:** {max_spieler} mit {round(max_punkte, 1)} Punkten nach Runde {runde_nummer}")

# 4. Beste Runde (höchster Einzelgewinn)
beste_runde = None
bester_spieler = None
max_gewinn = None
for sp in spieler:
    for i, g in enumerate(sp["gewinne"]):
        if max_gewinn is None or g > max_gewinn:
            max_gewinn = g
            bester_spieler = sp["name"]
            beste_runde = runden[i]["name"]

if max_gewinn is not None:
    st.markdown(f"💰 **Beste Einzelrunde:** {bester_spieler} in *{beste_runde}* (+{round(max_gewinn, 1)} Punkte)")
else:
    st.markdown("💰 Keine Gewinne vorhanden.")
