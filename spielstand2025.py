import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import altair as alt
import random
import streamlit_autorefresh
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="📺 Live Spielstand", layout="wide")

# Auto-Refresh alle 5 Minuten (300.000 Millisekunden)
streamlit_autorefresh.st_autorefresh(interval=300_000, key="refresh")

# 🔒 Fester Spielname – HIER ANPASSEN!
FESTER_SPIELNAME = "Vatertagsspiele 2025"

# Firebase verbinden
def get_firestore_client():
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firestore_client()

st.title("🎲 Vatertagsspiele 2025 - Spielstand (live)")

# Spiel laden
spiel_doc = db.collection("spiele").document(FESTER_SPIELNAME).get()
if not spiel_doc.exists:
    st.error(f"Spiel '{FESTER_SPIELNAME}' nicht gefunden.")
    st.stop()

daten = spiel_doc.to_dict()
spieler = daten["spieler"]
multiplikatoren = daten["multiplikatoren"]
runden = daten["runden"]
rundendaten = []
kommentare = daten.get("kommentare", [])

# Punkte berechnen
for sp in spieler:
    sp["einsaetze"], sp["plaetze"], sp["gewinne"] = [], [], []
    sp["punkte"] = 20.0

punkteverlauf = []
zwischenpunkte = {sp["name"]: 20.0 for sp in spieler}

bonus_empfaenger_pro_runde = []

for i, runde in enumerate(runden):
    rundenname = runde["name"]
    rundenzeit = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S")

    letzter_spieler = min(zwischenpunkte, key=zwischenpunkte.get)
    bonus_empfaenger_pro_runde.append(letzter_spieler)

    gewinne_der_runde = []

    for sp in spieler:
        einsatz = runde["einsaetze"].get(sp["name"], 0)
        platz = runde["plaetze"].get(sp["name"], 1)
        multiplikator = multiplikatoren[platz - 1] if platz - 1 < len(multiplikatoren) else 0
        gewinn = einsatz * multiplikator

        # Rubber-Banding: Kein Punktverlust für den Letztplatzierten der VORHERIGEN Runde
        if sp["name"] == letzter_spieler and gewinn < 0:
            gewinn = 0

        sp["einsaetze"].append(einsatz)
        sp["plaetze"].append(platz)
        sp["gewinne"].append(gewinn)
        sp["punkte"] += gewinn
        zwischenpunkte[sp["name"]] += gewinn
        gewinne_der_runde.append((sp["name"], gewinn))
        punkteverlauf.append({
            "Runde": f"{i+1}: {runde['name']}",
            "Spieler": sp["name"],
            "Punkte": zwischenpunkte[sp["name"]]
        })

    rundendaten.append({
    "runde": runde["name"],
    "zeit": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S"),
    "fuehrender": max(zwischenpunkte, key=zwischenpunkte.get),
    "letzter": min(zwischenpunkte, key=zwischenpunkte.get),
    "rundensieger": max(
        [(sp["name"], sp["gewinne"][i]) for sp in spieler],
        key=lambda x: x[1]
    ),
    "bonus": bonus_empfaenger_pro_runde[i],
})


kommentare_fuehrend = [
    "🥇 **{name}** führt jetzt mit {punkte:.1f} Punkten. Niemand stoppt diesen Siegeszug!",
    "🚀 **{name}** stürmt an die Spitze! {punkte:.1f} Punkte und kein Ende in Sicht!",
    "👑 **{name}** thront über allen mit {punkte:.1f} Punkten. Ein König unter Spielern!",
]

kommentare_letzter = [
    "🐢 **{name}** hinkt mit {punkte:.1f} Punkten hinterher. Vielleicht war das ein geheimer Plan?",
    "🪨 **{name}** hält das Feld stabil von hinten – {punkte:.1f} Punkte und viel Luft nach oben.",
    "🌌 **{name}** ist auf Entdeckungsreise im unteren Punktesektor ({punkte:.1f}).",
]

kommentare_rundensieger = [
    "💥 **{name}** schnappt sich diese Runde mit +{gewinn:.1f} Punkten. Boom!",
    "🔥 **{name}** dominiert die Runde! +{gewinn:.1f} Punkte sind kein Zufall.",
    "🎯 **{name}** trifft ins Schwarze – +{gewinn:.1f} Punkte in einer Runde!",
]

kommentare_bonus = [
    "🧲 **{name}** bekommt den Bonus – Letzter sein zahlt sich wohl doch aus!",
    "🔁 **{name}** nutzt Rubber-Banding – vielleicht klappt's ja nächstes Mal richtig!",
    "🎁 Bonuszeit für **{name}**! Manchmal ist Verlieren einfach lohnenswert.",
]

kommentare_bonus_gewinnt = [
    "⚡ **{name}** nutzt Rubber-Banding und rasiert die Runde mit +{gewinn:.1f} Punkten!",
    "👀 **{name}** kommt von hinten – mit Bonus +{gewinn:.1f} Punkte! Da staunt das Feld.",
    "🧨 **{name}** startet durch! Rubber-Banding at its best: +{gewinn:.1f} Punkte!",
]

# Kommentare generieren
aktueller_fuehrender = max(zwischenpunkte, key=zwischenpunkte.get)
aktueller_letzter = min(zwischenpunkte, key=zwischenpunkte.get)
rundensieger = max(gewinne_der_runde, key=lambda x: x[1])
bonus_empfaenger = letzter_spieler

# Kommentare für alle abgeschlossenen Runden (alle außer der letzten)
for j in range(len(rundendaten) - 1):
    rd = rundendaten[j]

    kommentarblock = f"### 🕓 Runde {j+1}: *{rd['runde']}* ({rd['zeit']})\n"
    kommentarblock += "- " + random.choice(kommentare_fuehrend).format(
        name=rd["fuehrender"], punkte=zwischenpunkte[rd["fuehrender"]]
    ) + "\n"
    kommentarblock += "- " + random.choice(kommentare_letzter).format(
        name=rd["letzter"], punkte=zwischenpunkte[rd["letzter"]]
    ) + "\n"
    kommentarblock += "- " + random.choice(kommentare_rundensieger).format(
        name=rd["rundensieger"][0], gewinn=rd["rundensieger"][1]
    ) + "\n"

    if rd["bonus"] == rd["rundensieger"][0]:
        kommentarblock += "- " + random.choice(kommentare_bonus_gewinnt).format(
            name=rd["bonus"], gewinn=rd["rundensieger"][1]
        ) + "\n"
    else:
        kommentarblock += "- " + random.choice(kommentare_bonus).format(
            name=rd["bonus"]
        ) + "\n"

    kommentare.append(kommentarblock)

    # 🔐 Kommentare speichern
    db.collection("spiele").document(FESTER_SPIELNAME).update({
        "kommentare": kommentare
    })


# Punktetabelle anzeigen
st.subheader("📊 Aktueller Punktestand")
tabelle = []
for sp in sorted(spieler, key=lambda x: -x["punkte"]):
    zeile = {"Spieler": sp["name"], "Punkte": round(sp["punkte"], 1)}
   # for i in range(len(runden)):
    for i in range(len(runden) - 1, -1, -1):
        bonus = "★" if sp["name"] == bonus_empfaenger_pro_runde[i] else ""
        zeile[runden[i]["name"]] = f"E: {sp['einsaetze'][i]} | P: {sp['plaetze'][i]} | +{round(sp['gewinne'][i],1)}{bonus}"
    tabelle.append(zeile)

df = pd.DataFrame(tabelle)
st.dataframe(df, use_container_width=True, hide_index=True)

#Spielkommentare anzeigen
st.subheader("💬 Spielkommentar")
if kommentare:
    st.markdown(kommentare[0])
else:
    st.info("Noch kein Kommentar verfügbar.")

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

# 📊 Spielstatistiken anzeigen
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

#Spielkommentare anzeigen    
st.subheader("💬 Spielkommentare")
# Alle Kommentare außer dem letzten anzeigen
for kommentar in kommentare[:-1]:  # [: -1] = alles außer letzter Eintrag
    with st.expander(kommentar.split("\n")[0]):
        st.markdown("\n".join(kommentar.split("\n")[1:]))



aktuelle_runde_index = len(runden) - 1  # Index der letzten Runde (0-basiert)
aktuelle_runde_name = f"{len(runden)}: {runden[-1]['name']}"
