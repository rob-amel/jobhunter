import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import time
import json
import google.generativeai as genai

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="🌍 Job Hunter Pro", layout="centered")
st.title("🌍 Job Hunter Pro")

# Recupero API KEY
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    st.error("❌ Chiave API mancante! Inseriscila nei secrets.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# --- 2. FUNZIONE PER TROVARE IL MODELLO GIUSTO ---
def trova_modello_disponibile():
    """Cerca un modello valido supportato dalla tua API Key"""
    pref_list = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
    
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 1. Cerca il preferito (Flash)
        for pref in pref_list:
            if pref in available_models:
                return pref
        
        # 2. Se non trova i preferiti, prendi il primo disponibile generico
        if available_models:
            return available_models[0]
            
    except Exception as e:
        st.error(f"Errore nel listare i modelli: {e}")
        return "models/gemini-pro" # Fallback disperato
    
    return "models/gemini-pro"

# --- 3. FUNZIONE RICERCA ---
def cerca_lavoro_ai(profilo, keywords, paese):
    
    # Trova il modello dinamicamente
    model_name = trova_modello_disponibile()
    st.info(f"🤖 Utilizzo modello: `{model_name}`") # Feedback per l'utente

    # Configurazione
    generation_config = {
        "temperature": 0.5,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config
    )

    prompt = f"""
    Sei un recruiter. 
    Profilo: {profilo[:3000]}
    Task: Trova 5 job roles per "{keywords}" in "{paese}".
    
    Output richiesto: Un ARRAY JSON puro con questa struttura:
    [
      {{
        "titolo_lavoro": "...",
        "organizzazione": "...",
        "luogo": "...",
        "deadline": "...",
        "link": "...",
        "riassunto": "..."
      }}
    ]
    """

    try:
        response = model.generate_content(prompt)
        # Pulizia del testo per essere sicuri che sia JSON
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp.replace("```json", "").replace("```", "")
        
        return json.loads(text_resp)

    except Exception as e:
        st.error(f"Errore durante la generazione ({model_name}): {e}")
        return None

# --- 4. INTERFACCIA ---
st.sidebar.header("Carica CV")
uploaded_files = st.sidebar.file_uploader("PDF", type="pdf", accept_multiple_files=True)
profile_text = ""

if uploaded_files:
    for f in uploaded_files:
        try:
            reader = PdfReader(f)
            for page in reader.pages:
                profile_text += (page.extract_text() or "") + "\n"
        except:
            pass
    st.sidebar.success(f"CV Caricato.")

col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo", "Project Manager")
with col2: ps = st.text_input("Paese", "Kenya")

if st.button("🚀 CERCA", type="primary"):
    with st.spinner("Connessione all'IA..."):
        p_text = profile_text if profile_text else "Nessun CV."
        data = cerca_lavoro_ai(p_text, kw, ps)
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("Scarica Excel", buffer.getvalue(), "jobs.xlsx")
        else:
            st.warning("Nessun risultato trovato.")
