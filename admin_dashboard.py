import pandas as pd
import streamlit as st
import psycopg2
import ast

st.set_page_config(page_title="AP-48 – panel administratora", layout="wide")

# ------------ USTAWIENIA POŁĄCZENIA (z .streamlit/secrets.toml na Streamlit Cloud) ------------
db_host = st.secrets["db_host"]
db_name = st.secrets["db_name"]
db_user = st.secrets["db_user"]
db_pass = st.secrets["db_pass"]
db_port = st.secrets.get("db_port", 5432)  # jeśli ustawiasz własny port

# ------------ FUNKCJA POBIERANIA ------------
@st.cache_data(ttl=30)
def load():
    # Połącz z bazą PostgreSQL (Supabase)
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_pass,
        port=db_port
    )
    df = pd.read_sql("SELECT * FROM ap48_responses", con=conn)
    conn.close()
    # Przerób timestamps na datetime
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    # Rozbij kolumnę 'scores' (jsonb) na kolumny
    if "scores" in df.columns:
        scores_df = df["scores"].apply(lambda x: pd.Series(ast.literal_eval(x)) if pd.notnull(x) else None)
        df = pd.concat([df, scores_df], axis=1)
    return df

# ------------ INTERFEJS ------------
st.title("AP-48 – panel administratora")

data = load()

st.metric("Łączna liczba ankiet", len(data))

if "raw_total" in data.columns and "created_at" in data.columns:
    st.line_chart(data.set_index("created_at")["raw_total"].resample("D").mean())

for col in ["Skala_A", "Skala_B", "Skala_C", "Skala_D"]:
    if col in data.columns:
        st.subheader(col)
        st.bar_chart(data[col])

# Eksport CSV
st.download_button("Pobierz dane CSV", data.to_csv(index=False), "ap48.csv")