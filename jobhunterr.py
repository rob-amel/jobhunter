import streamlit as st
import pandas as pd
import pypdf
import io
import os
from io import BytesIO, StringIO
from datetime import datetime
from google import genai
from google.genai import types

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="🌍 Job Hunter AI Pro", layout="centered")

# Recupero chiave come in Lino Bandi 2
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- STILE BOTTONE ROSSO ---
st.markdown("""
<style>
.stDownloadButton > button {
    background-color: #FF4B4B !important;
    color: white !important;
    font-weight: bold;
    width: 100%;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI Pro")
st.markdown("Basato sulla tecnologia di **Lino Bandi 2** per una ricerca lavoro infallibile.")

# --- SIDEBAR: PROFILO ---
st.sidebar.header("📄 Il tuo Profilo")
uploaded_files = st.sidebar.file_uploader("Carica fino a 5 PDF (CV/Bio)", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            profile_context += page.extract_text() + "\n"
    st.sidebar.success("Profilo analizzato!")

# --- AREA DI RICERCA ---
st.header("🔍 Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Quale ruolo cerchi?", placeholder="es. Project Manager WASH")
with col2:
    country = st.text_input("In quale Paese?", placeholder="es. Sudan o Remote")

search_strategy = st.radio("Sorgente:", ["Siti Specifici (ReliefWeb, Info-Coop, UNJobs)", "Tutto il Web"], horizontal=True)

# --- FUNZIONE DI ANALISI (LOGICA LINO BANDI 2) ---
def cerca_lavoro_ai(profilo, query, strategia):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Usiamo il modello Flash 2.0 (o 1.5 se preferisci) come nel tuo codice funzionante
        model_id = 'gemini-2.0-flash' # Oppure 'gemini-1.5-flash'
        
        prompt = f"""
        Sei un esperto HR internazionale. Analizza il profilo del candidato e la sua ricerca.
        PROFILO: {profilo[:2000]}
        RICERCA: {query} su {strategia}
        
        Genera 5 opportunità di lavoro. Rispondi SOLO in formato CSV usando il punto e virgola ';' come separatore.
        Colonne: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
        """
        
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        text_out = response.text.strip()
        # Pulizia markdown
        if "```" in text_out:
            text_out = text_out.split("```")[1].replace("csv", "").strip()
        
        return pd.read_csv(StringIO(text_out), sep=";", on_bad_lines='skip')
    except Exception as e:
        st.error(f"Errore AI: {e}")
        return None

# --- AZIONE ---
if st.button("🚀 AVVIA JOB HUNTER", type="primary"):
    if not (keywords and country):
        st.warning("Inserisci i dati per la ricerca.")
    else:
        with st.spinner("L'IA sta scansionando il web per te..."):
            df_risultati = cerca_lavoro_ai(profile_context, f"{keywords} {country}", search_strategy)
            
            if df_risultati is not None:
                st.write("### 📊 Opportunità individuate")
                st.dataframe(df_risultati)
                
                # Excel Download
                output = BytesIO()
                df_risultati.to_excel(output, index=False, engine='xlsxwriter')
                
                st.markdown("---")
                st.download_button(
                    label="📥 SCARICA REPORT EXCEL (ROSSO)",
                    data=output.getvalue(),
                    file_name=f"Job_Hunter_{country}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
