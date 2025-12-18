import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import json
import google.generativeai as genai
from jobspy import scrape_jobs

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Job Hunter Pro - Document Intelligence", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FUNZIONE AUTO-DISCOVERY MODELLO (Risolve il 404) ---
def ottieni_modello_valido():
    """Trova il miglior modello disponibile per evitare l'errore 404"""
    try:
        modelli_disponibili = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Ordine di preferenza
        preferiti = [
            'models/gemini-1.5-flash', 
            'models/gemini-1.5-pro', 
            'models/gemini-pro',
            'models/gemini-1.0-pro'
        ]
        for p in preferiti:
            if p in modelli_disponibili:
                return p
        return modelli_disponibili[0] if modelli_disponibili else None
    except Exception as e:
        st.error(f"Impossibile elencare i modelli: {e}")
        return None

# --- FUNZIONE ANALISI INTEGRATA ---
def analizza_e_matcha(testo_documenti, keywords, paese):
    model_name = ottieni_modello_valido()
    
    if not model_name:
        st.error("Nessun modello Gemini trovato per questa API Key.")
        return None

    st.info(f"Modello in uso: `{model_name}`")

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )

        prompt = f"""
        Analizza questi documenti: {testo_documenti[:8000]}
        
        1. Calcola gli anni di esperienza per OGNI ruolo e somma il totale pertinente per: "{keywords}".
        2. Trova 5 offerte in "{paese}" adatte ESATTAMENTE a quel livello.
        3. Escludi offerte Senior se il candidato non ha almeno 6-7 anni di esperienza specifica.

        RESTITUISCI SOLO JSON:
        {{
          "profilo_estratto": {{
            "anni_totali": "numero",
            "competenze_chiave": ["...", "..."],
            "analisi_cronologica": "sintesi delle date e ruoli trovati"
          }},
          "match_offerte": [
            {{
              "titolo": "...",
              "azienda": "...",
              "data_inizio": "...",
              "anni_richiesti_offerta": "...",
              "match_score": "...",
              "motivazione_match": "spiega il match tra i suoi anni reali e l'offerta",
              "requisiti_specifici": "...",
              "link": "..."
            }}
          ]
        }}
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        # Pulizia markdown se presente
        if text.startswith("```json"): text = text[7:-3]
        if text.startswith("```"): text = text[3:-3]
        
        return json.loads(text)
    except Exception as e:
        st.error(f"Errore durante l'analisi: {e}")
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
with col1: kw = st.text_input("Ruolo desiderato")
with col2: ps = st.text_input("Area Geografica")

if st.button("🚀 ANALIZZA E TROVA MATCH", type="primary"):
    if not profile_text:
        st.warning("Carica i file PDF.")
    else:
        with st.spinner("L'IA sta verificando la tua cronologia lavorativa..."):
            risultato = analizza_e_matcha(profile_text, kw, ps)
            
            if risultato:
                st.subheader("👤 Analisi del Profilo")
                prof = risultato['profilo_estratto']
                c1, c2 = st.columns([1, 4])
                c1.metric("Anni Esperienza", f"{prof['anni_totali']} yrs")
                c2.write(f"**Esperienza Cronologica:** {prof['analisi_cronologica']}")
                
                st.divider()

                for item in risultato['match_offerte']:
                    with st.expander(f"📌 {item['titolo']} - {item['azienda']}"):
                        st.write(f"**Match:** {item['match_score']} | **Anni Richiesti:** {item['anni_richiesti_offerta']}")
                        st.write(f"**Motivazione:** {item['motivazione_match']}")
                        st.write(f"**Requisiti:** {item['requisiti_specifici']}")
                        st.write(f"**Link:** {item['link']}")
