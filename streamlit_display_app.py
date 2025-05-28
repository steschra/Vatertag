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

st.subheader("📌 Spielstatistiken")
# 1. Häufigster Rundensieger
rundensieger_namen = [runde["rundensieger"][0] for runde in rundendaten]
rundensieger_counts = pd.Series(rundensieger_namen).value_counts()
haeufigster_rundensieger = rundensieger_counts.idxmax()
rundensieger_anzahl = rundensieger_counts.max()

# 2. Höchster Punktestand im Spielverlauf
df_punkte_max = pd.DataFrame(punkteverlauf)
max_row = df_punkte_max.loc[df_punkte_max["Punkte"].idxmax()]
max_punkte = max_row["Punkte"]
max_punkte_spieler = max_row["Spieler"]
max_punkte_runde = max_row["Runde"]

# 3. Häufigster Rubber-Banding-Spieler (Bonus-Empfänger)
bonus_counter = pd.Series(bonus_empfaenger_pro_runde)
haeufigster_bonus_spieler = bonus_counter.value_counts().idxmax()
bonus_anzahl = bonus_counter.value_counts().max()

# 4. Meiste Punkte in einer einzelnen Runde
beste_runde = None
max_gewinn = -1
gewinner = None
rundenname = ""

for runden_index, runde in enumerate(rundendaten):
    name, gewinn = runde["rundensieger"]
    if gewinn > max_gewinn:
        max_gewinn = gewinn
        gewinner = name
        rundenname = f"{runden_index + 1}: {runde['runde']}"

# Darstellung in vier Spalten
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏆 Häufigster Rundensieger", f"{haeufigster_rundensieger}", f"{rundensieger_anzahl}×")

with col2:
    st.metric("💯 Höchster Punktestand ever", f"{max_punkte_spieler}", f"{max_punkte:.1f} Punkte ({max_punkte_runde})")

with col3:
    st.metric("🎁 Häufigster Rubber-Banding-Nutzer", f"{haeufigster_bonus_spieler}", f"{bonus_anzahl}×")

with col4:
    st.metric("🔥 Meisten Punkte in einem Spiel", f"{gewinner}", f"+{max_gewinn:.1f} Punkte ({rundenname})")
