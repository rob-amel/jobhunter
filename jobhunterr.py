import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
from datetime import datetime
from google import genai
from google.genai import types

# --- CONFIGURAZIONE CHIAVE ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- SCHEMA DI OUTPUT (Copiato dalla logica Lino Bandi 2) ---
output_schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "jobs": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "titolo lavoro": types.Schema(type=types.Type.STRING),
                    "organizzazione proponente": types.Schema(type=types.Type.STRING),
                    "luogo": types.Schema(type=types.Type.STRING),
                    "data di inizio": types.Schema(type=types.Type.STRING),
                    "deadline": types.Schema(type=types.Type.STRING),
                    "contenuto proposta": types.Schema(type=types.Type.STRING),
                    "requisiti": types.Schema(type=types.Type.STRING),
                    "link": types.Schema(type=types.Type.STRING),
                }
            )
        )
    }
)

# --- FUNZIONE DI ESTRAZIONE (Logica Identica a Lino Bandi 2) ---
def cerca_lavoro_ai(profilo, keywords, paese, strategia):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        Sei un esperto HR. Analizza il profilo: {profilo[:2000]}
        Trova 5 opportunità per: {keywords} in {paese} (Sorgente: {strategia}).
        Usa i siti: ReliefWeb, Info-Cooperazione, UNJobs.
        Compila tutti i campi richiesti in italiano. Se mancano info usa 'NA'.
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash', # Il modello che ti funziona in Lino Bandi 2
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=output_schema,
            ),
        )
        return response.parsed # Restituisce direttamente l'oggetto strutturato
    except Exception as e:
        st.error(f"Errore durante l'analisi: {e}")
        return None

# --- INTERFACCIA ---
st.set_page_config(page_title="🌍 Job Hunter Pro", layout="centered")
st.title("🌍 Job Hunter Pro")

# Caricamento PDF
st.sidebar.header("📄 Tuo Profilo")
uploaded_files = st.sidebar.file_uploader("Carica CV (max 5)", type="pdf", accept_multiple_files=True)

profile_text = ""
if uploaded_files:
    for f in uploaded_files[:5]:
        reader = PdfReader(f)
        for page in reader.pages:
            profile_text += page.extract_text() + "\n"
    st.sidebar.success("Profilo pronto!")

# Input
col1, col2 = st.columns(2)
with col1:
    kw = st.text_input("Ruolo:")
with col2:
    ps = st.text_input("Paese:")
strat = st.radio("Sito:", ["Specifici", "Tutto il Web"], horizontal=True)

if st.button("🚀 AVVIA RICERCA", type="primary"):
    if not (kw and ps):
        st.warning("Inserisci i dati.")
    else:
        with st.spinner("L'IA sta lavorando con la logica 'Lino Bandi'..."):
            risultato = cerca_lavoro_ai(profile_text, kw, ps, strat)
            
            if risultato and hasattr(risultato, 'jobs'):
                df = pd.DataFrame(risultato.jobs)
                st.dataframe(df)

                # Bottone Rosso Excel
                st.markdown("<style>.stDownloadButton>button{background-color:#FF4B4B;color:white;font-weight:bold;width:100%}</style>", unsafe_allow_html=True)
                
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='xlsxwriter')
                st.download_button("📥 SCARICA EXCEL", output.getvalue(), f"Jobs_{ps}.xlsx")
