import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import json
import google.generativeai as genai
from jobspy import scrape_jobs
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Job Hunter Pro - Tailored Edition", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FUNZIONE SCRAPING (Resiliente) ---
def ricerca_reale_web(ruolo, paese):
    try:
        # Nota: usiamo parametri generici per evitare errori di versione
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=ruolo,
            location=paese,
            results_wanted=7,
            country_specific=paese.lower() if len(paese) == 2 else None,
        )
        return jobs
    except Exception as e:
        st.error(f"Errore scraping: {e}")
        return pd.DataFrame()

# --- FUNZIONE ANALISI IA TAILORED ---
def cerca_lavoro_ai(profilo, keywords, paese, anni_utente):
    # Selezione dinamica del modello
    try:
        model_name = "gemini-1.5-flash"
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
        )

        prompt = f"""
        Sei un Senior Recruiter. Il candidato ha esattamente {anni_utente} anni di esperienza professionale.
        
        Analizza attentamente questo CV: {profilo[:4000]}
        
        REGOLE MANDATORIE:
        1. Trova 5 lavori per "{keywords}" in "{paese}".
        2. NON proporre lavori che richiedono più di {anni_utente} anni di esperienza. Se il lavoro richiede "Senior" o "7+ anni", SCARTALO.
        3. Se il CV non ha competenze specifiche richieste da un lavoro, segnalalo nel campo 'gap_analisi'.

        Restituisci un ARRAY JSON con questa struttura esatta:
        [
          {{
            "titolo_lavoro": "...",
            "organizzazione": "...",
            "luogo": "...",
            "data_inizio": "...",
            "anni_esperienza_richiesti": "...",
            "requisiti_specifici": "...",
            "perche_adatto": "Spiega brevemente il match con i {anni_utente} anni del candidato",
            "gap_analisi": "Quali competenze mancano al candidato per questa posizione?",
            "link": "..."
          }}
        ]
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:-3]
        return json.loads(text)
    except Exception as e:
        st.error(f"Errore IA: {e}")
        return None

# --- INTERFACCIA ---
st.title("🌍 Job Hunter Pro: Ricerca Su Misura")

with st.sidebar:
    st.header("📄 Analisi Profilo")
    uploaded_files = st.file_uploader("Carica CV (PDF)", type="pdf")
    
    # Parametro critico: Anni di esperienza
    anni_exp = st.number_input("I tuoi anni di esperienza effettivi:", min_value=0, max_value=40, value=4)
    
    profile_text = ""
    if uploaded_files:
        reader = PdfReader(uploaded_files)
        for page in reader.pages:
            profile_text += (page.extract_text() or "") + "\n"
        st.success("CV Caricato!")

col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo", placeholder="es. Project Manager")
with col2: ps = st.text_input("Località", placeholder="es. Milano, Italy")

if st.button("🚀 AVVIA RICERCA TAILORED", type="primary"):
    if not (kw and ps):
        st.warning("Compila i campi Ruolo e Località.")
    else:
        with st.spinner(f"Filtrando posizioni adatte per {anni_exp} anni di esperienza..."):
            
            # 1. Ricerca Live
            df_reale = ricerca_reale_web(kw, ps)
            
            # 2. Analisi IA con filtro anni
            dati_ai = cerca_lavoro_ai(profile_text, kw, ps, anni_exp)

        # Visualizzazione
        if dati_ai:
            df_final = pd.DataFrame(dati_ai)
            
            st.subheader(f"🎯 Top 5 Match per il tuo profilo ({anni_exp} anni exp.)")
            
            # Formattazione per rendere i risultati leggibili
            for i, row in df_final.iterrows():
                with st.expander(f"📌 {row['titolo_lavoro']} - {row['organizzazione']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**📍 Luogo:** {row['luogo']}")
                        st.write(f"**⏳ Esperienza Richiesta:** {row['anni_esperienza_richiesti']}")
                        st.write(f"**📅 Inizio:** {row['data_inizio']}")
                    with c2:
                        st.success(f"**✅ Perché è adatto:** {row['perche_adatto']}")
                        if row['gap_analisi']:
                            st.warning(f"**⚠️ Gap da colmare:** {row['gap_analisi']}")
                    
                    st.write(f"**🛠 Requisiti:** {row['requisiti_specifici']}")
                    st.write(f"**🔗 Link:** {row['link']}")

            # Export Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False)
            st.download_button("📥 Scarica Report Excel", output.getvalue(), "lavori_su_misura.xlsx")
        else:
            st.error("Non è stato possibile generare risultati su misura.")

        if not df_reale.empty:
            with st.expander("🌐 Vedi altri annunci trovati sul Web (Non filtrati)"):
                st.dataframe(df_reale[['title', 'company', 'location', 'job_url']])
