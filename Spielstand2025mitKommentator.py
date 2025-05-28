import streamlit as st
import pyrebase
import pandas as pd

st.set_page_config(page_title="Vatertagsspiele 2025 – Live", layout="wide")

# Firebase-Konfiguration
firebase_config = {
    "apiKey": "AIzaSyD3E...",
    "authDomain": "vatertagsspiele.firebaseapp.com",
    "databaseURL": "https://vatertagsspiele.firebaseio.com",
    "storageBucket": "vatertagsspiele.appspot.com"
}

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Daten abrufen
spiel_id = "vatertag2025"
spiel = db.child("spiele").child(spiel_id).get().val()
spieler = db.child("spieler").order_by_child("spiel_id").equal_to(spiel_id).get().val()
runden = db.child("runden").order_by_child("spiel_id").equal_to(spiel_id).get().val()
multiplikatoren = db.child("multiplikatoren").child(spiel_id).get().val()

# Sicherstellen, dass Session-State gesetzt ist
if "spieler" not in st.session_state:
    st.session_state.spieler = list(spieler.values()) if spieler else []
if "runden" not in st.session_state:
    st.session_state.runden = list(runden.values()) if runden else []
if "multiplikatoren" not in st.session_state:
    st.session_state.multiplikatoren = multiplikatoren if multiplikatoren else {}

# Live Punkteverlauf und Gewinnanalyse vorbereiten
punkteverlauf = []
gewinnerliste = []
kommentare = []
bonus_empfaenger_pro_runde = []

zwischenpunkte = {sp["name"]: 20.0 for sp in st.session_state.spieler}

for runden_idx, runde in enumerate(st.session_state.runden):
    name = runde.get("name", f"Runde {runden_idx+1}")
    runden_multiplikator = st.session_state.multiplikatoren.get(str(runden_idx), 1)
    einsaetze = {sp["name"]: sp["einsaetze"][runden_idx] for sp in st.session_state.spieler}
    gewinne = {sp["name"]: sp["gewinne"][runden_idx] for sp in st.session_state.spieler}

    top_punkte = -999
    top_spieler = None
    kommentar = ""
    bonus_empfaenger = []

    for sp in st.session_state.spieler:
        name = sp["name"]
        einsatz = einsaetze[name]
        gewinn = gewinne[name]
        punkte = einsatz * gewinn * runden_multiplikator
        zwischenpunkte[name] += punkte
        punkteverlauf.append({
            "Spieler": name,
            "Runde": f"{runden_idx + 1}: {runde['name']}",
            "Punkte": zwischenpunkte[name]
        })
        if punkte > top_punkte:
            top_punkte = punkte
            top_spieler = name

    # Bonusvergabe
    min_punkte = min(zwischenpunkte.values())
    bonus_empfaenger = [name for name, p in zwischenpunkte.items() if p == min_punkte]
    for name in bonus_empfaenger:
        zwischenpunkte[name] += 1  # Bonuspunkt
    bonus_empfaenger_pro_runde.append(bonus_empfaenger)

    kommentar = f"**{top_spieler}** gewinnt Runde **{runden_idx+1} – {runde['name']}** mit **{top_punkte:.1f} Punkten**."
    if bonus_empfaenger:
        kommentar += f" Bonuspunkt für: {', '.join(bonus_empfaenger)}"
    kommentare.append(kommentar)

# Punktetabelle erzeugen
df = pd.DataFrame([
    {"Spieler": name, "Punkte": punkte}
    for name, punkte in zwischenpunkte.items()
]).sort_values(by="Punkte", ascending=False)

# HTML-Tabelle mit Bonusanzeige
table_html = "<table style='width:100%; border-collapse: collapse;'>"
table_html += "<tr><th style='text-align:left;'>Spieler</th><th style='text-align:right;'>Punkte</th></tr>"

for index, row in df.iterrows():
    is_bonus = any(row["Spieler"] in bonus for bonus in bonus_empfaenger_pro_runde)
    bonus_style = "background-color: #fffae6;" if is_bonus else ""
    table_html += f"<tr style='{bonus_style}'><td>{row['Spieler']}</td><td style='text-align:right;'>{row['Punkte']:.1f}</td></tr>"

table_html += "</table>"

# Streamlit UI
st.title("🎲 Vatertagsspiele 2025 – Live")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🏆 Aktueller Spielstand")
    st.markdown(table_html, unsafe_allow_html=True)

with col2:
    st.subheader("📈 Punkteverlauf")
    df_chart = pd.DataFrame(punkteverlauf)
    if not df_chart.empty:
        st.line_chart(df_chart.pivot(index="Runde", columns="Spieler", values="Punkte"))

st.subheader("📝 Spielkommentare")
for kommentar in kommentare:
    with st.expander(kommentar[:120] + "..."):
        st.markdown(kommentar)
