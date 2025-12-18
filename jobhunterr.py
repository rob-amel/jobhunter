import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import json
import google.generativeai as genai
from jobspy import scrape_jobs
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Job Hunter Pro + Real Search", layout="wide")

# --- RECUPERO API KEY ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FUNZIONE 1: RICERCA REALE (JOBSPY) ---
def ricerca_reale_web(ruolo, paese):
    try:
        # Nota: JobSpy cerca su LinkedIn, Indeed, Glassdoor simultaneamente
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=ruolo,
            location=paese,
            results_wanted=5,
            hours_old=72, 
            country_specific=paese.lower(),
        )
        return jobs
    except Exception as e:
        st.error(f"Errore durante lo scraping reale: {e}")
        return pd.DataFrame()

# --- FUNZIONE 2: ANALISI IA (GEMINI) ---
def cerca_lavoro_ai(profilo, keywords, paese):
    # Cerchiamo il modello disponibile come nel passaggio precedente
    def get_model():
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            for m in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
                if m in available: return m
            return available[0] if available else "models/gemini-pro"
        except: return "models/gemini-pro"

    model_name = get_model()
    
    generation_config = {
        "temperature": 0.3,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)

    prompt = f"""
    Sei un recruiter esperto. Analizza questo CV: {profilo[:4000]}
    
    Trova 5 opportunità (anche simulate basate su aziende reali del settore) per "{keywords}" in "{paese}".
    Per ogni posizione, sii molto preciso.
    
    Restituisci esclusivamente un ARRAY JSON con questo formato:
    [
      {{
        "titolo_lavoro": "...",
        "organizzazione": "...",
        "luogo": "...",
        "data_inizio_stimata": "...",
        "anni_esperienza_richiesti": "...",
        "requisiti_specifici": "...",
        "link_fonte": "...",
        "match_con_cv_percentuale": "..."
      }}
    ]
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:-3]
        return json.loads(text)
    except:
        return None

# --- INTERFACCIA UTENTE ---
st.title("🌍 Job Hunter Pro v2.0")
st.markdown("### Ricerca Ibrida: Web Scraping Reale + Analisi IA")

with st.sidebar:
    st.header("📄 Il tuo Profilo")
    uploaded_files = st.file_uploader("Carica CV (PDF)", type="pdf", accept_multiple_files=True)
    profile_text = ""
    if uploaded_files:
        for f in uploaded_files:
            reader = PdfReader(f)
            for page in reader.pages:
                profile_text += (page.extract_text() or "") + "\n"
        st.success("CV analizzato correttamente.")

col1, col2 = st.columns(2)
with col1: kw = st.text_input("Che lavoro cerchi?", placeholder="es. Senior Data Analyst")
with col2: ps = st.text_input("Dove?", placeholder="es. Italy o Switzerland")

if st.button("🚀 AVVIA RICERCA INTEGRATA", type="primary"):
    if not (kw and ps):
        st.warning("Inserisci ruolo e località.")
    else:
        # --- PARTE 1: RICERCA REALE ---
        with st.spinner("🕵️‍♂️ Scraping in corso su LinkedIn, Indeed e Glassdoor..."):
            df_reale = ricerca_reale_web(kw, ps)
            
        # --- PARTE 2: ANALISI IA ---
        with st.spinner("🤖 L'intelligenza artificiale sta elaborando i dettagli..."):
            dati_ai = cerca_lavoro_ai(profile_text, kw, ps)

        # --- VISUALIZZAZIONE RISULTATI ---
        tab1, tab2 = st.tabs(["📊 Report Completo IA", "🌐 Risultati Web Diretti"])
        
        with tab1:
            if dati_ai:
                final_df = pd.DataFrame(dati_ai)
                st.write("### 💎 Opportunità Selezionate per Te")
                st.table(final_df) # Usiamo table per vedere bene i requisiti lunghi
                
                # Download Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='Opportunità')
                st.download_button("📥 Scarica Report Excel Completo", output.getvalue(), f"Jobs_{ps}_{datetime.now().strftime('%d%m')}.xlsx")
            else:
                st.error("L'IA non è riuscita a generare il report.")

        with tab2:
            if not df_reale.empty:
                st.write("### 🔍 Ultimi annunci trovati live")
                # Selezioniamo solo colonne interessanti per pulizia
                cols = ['title', 'company', 'location', 'job_url']
                st.dataframe(df_reale[cols] if all(c in df_reale.columns for c in cols) else df_reale)
            else:
                st.info("Nessun annuncio recente trovato via web scraping. Affidati al report IA.")
