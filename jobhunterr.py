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
st.set_page_config(page_title="Job Hunter Pro - Document Intelligence", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FUNZIONE SCRAPING ---
def ricerca_reale_web(ruolo, paese):
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=ruolo,
            location=paese,
            results_wanted=10,
            country_specific=paese.lower() if len(paese) == 2 else None,
        )
        return jobs
    except Exception as e:
        return pd.DataFrame()

# --- FUNZIONE ANALISI INTEGRATA ---
def analizza_e_matcha(testo_documenti, keywords, paese):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )

        # Il prompt ora chiede prima un'analisi interna dei documenti e poi il match
        prompt = f"""
        TASK:
        1. Analizza i seguenti documenti (CV, Certificazioni, Lettere): {testo_documenti[:8000]}
        2. Costruisci un profilo professionale calcolando con precisione gli anni di esperienza per OGNI ruolo ricoperto.
        3. Somma l'esperienza totale pertinente per la posizione: "{keywords}".
        4. Trova 5 offerte in "{paese}" che corrispondano ESATTAMENTE a questo livello di anzianità.
        
        REGOLE DI FILTRO:
        - Se il candidato ha 4 anni di esperienza totale, escludi tassativamente offerte "Senior" da 7-10 anni.
        - Se un'offerta richiede competenze tecniche non presenti nei documenti, segnalalo come 'GAP'.

        RESTITUISCI UN JSON:
        {{
          "profilo_estratto": {{
            "anni_totali": "numero",
            "competenze_chiave": ["...", "..."],
            "analisi_cronologica": "breve sintesi dei ruoli trovati"
          }},
          "match_offerte": [
            {{
              "titolo": "...",
              "azienda": "...",
              "data_inizio": "...",
              "anni_richiesti_offerta": "...",
              "match_score": "percentuale",
              "motivazione_match": "spiega il confronto tra i suoi anni e quelli dell'offerta",
              "requisiti_specifici": "...",
              "link": "..."
            }}
          ]
        }}
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:-3]
        return json.loads(text)
    except Exception as e:
        st.error(f"Errore Analisi: {e}")
        return None

# --- INTERFACCIA ---
st.title("🌍 Job Hunter Pro: Document Intelligence")

with st.sidebar:
    st.header("📂 Documentazione")
    uploaded_files = st.file_uploader("Carica CV e Documenti (PDF)", type="pdf", accept_multiple_files=True)
    
    profile_text = ""
    if uploaded_files:
        for f in uploaded_files:
            reader = PdfReader(f)
            for page in reader.pages:
                profile_text += (page.extract_text() or "") + "\n"
        st.success(f"Analizzati {len(uploaded_files)} documenti.")

col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo desiderato", placeholder="es. Humanitarian Project Manager")
with col2: ps = st.text_input("Area Geografica", placeholder="es. Dakar, Senegal")

if st.button("🚀 ANALIZZA DOCUMENTI E TROVA MATCH", type="primary"):
    if not profile_text:
        st.warning("Carica almeno un documento per l'analisi.")
    elif not (kw and ps):
        st.warning("Inserisci Ruolo e Area Geografica.")
    else:
        with st.spinner("L'IA sta leggendo i tuoi documenti e calcolando la tua esperienza..."):
            
            risultato = analizza_e_matcha(profile_text, kw, ps)
            
            if risultato:
                # --- Sezione Profilo Estratto ---
                st.subheader("👤 Profilo Ricostruito dall'IA")
                prof = risultato['profilo_estratto']
                c1, c2, c3 = st.columns([1, 2, 2])
                c1.metric("Anni Esperienza", f"{prof['anni_totali']} yrs")
                c2.write(f"**Competenze individuate:** {', '.join(prof['competenze_chiave'])}")
                c3.info(f"**Sintesi Carriera:** {prof['analisi_cronologica']}")
                
                st.divider()

                # --- Sezione Match ---
                st.subheader("🎯 Offerte Tailored individuate")
                df_match = pd.DataFrame(risultato['match_offerte'])
                
                for item in risultato['match_offerte']:
                    with st.expander(f"📌 {item['titolo']} @ {item['azienda']} (Match: {item['match_score']})"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**⏳ Richiesti dall'azienda:** {item['anni_richiesti_offerta']}")
                            st.write(f"**📅 Inizio:** {item['data_inizio']}")
                            st.write(f"**🔗 Link:** {item['link']}")
                        with col_b:
                            st.write(f"**⚖️ Analisi Compatibilità:** {item['motivazione_match']}")
                            st.write(f"**🛠 Requisiti:** {item['requisiti_specifici']}")

                # Download Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_match.to_excel(writer, index=False)
                st.download_button("📥 Scarica Report Excel", output.getvalue(), "match_lavoro_tailored.xlsx")
            else:
                st.error("Errore nell'elaborazione dei dati.")
