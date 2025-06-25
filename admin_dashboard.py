import pandas as pd
import streamlit as st
from supabase import create_client, Client

url = st.secrets["supabase_url"]
key = st.secrets["service_role_key"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=30)
def load():
    res = supabase.table("ap48_responses").select("*").execute()
    df = pd.DataFrame(res.data)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return pd.concat([df, df["scores"].apply(pd.Series)], axis=1)

st.title("AP-48 – panel administratora")
data = load()
st.metric("Łączna liczba ankiet", len(data))
st.line_chart(data.set_index("created_at")["raw_total"].resample("D").mean())

for col in ["Skala_A","Skala_B","Skala_C","Skala_D"]:
    st.subheader(col)
    st.bar_chart(data[col])