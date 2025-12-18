import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import time
import json
import google.generativeai as genai
from google.api_core import retry

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="🌍 Job Hunter Pro", layout="centered")
st.title("🌍 Job Hunter Pro")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("❌ Chiave API mancante! Inseriscila nei secrets.")

# --- 2. DEBUG MODELLI DISPONIBILI ---
# Questo blocco aiuta a capire se la libreria vede i modelli giusti
with st.expander("🛠️ Debug: Verifica Modelli Disponibili"):
    if st.button("Controlla Modelli"):
        try:
            st.write("Cercando modelli...")
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            st.success(f"Modelli trovati: {available_models}")
        except Exception as e:
            st.error(f"Errore nel recupero modelli: {e}")

# --- 3. SCHEMA JSON ---
response_schema = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "titolo_lavoro": {"type": "STRING"},
            "organizzazione": {"type": "STRING"},
            "luogo": {"type": "STRING"},
            "deadline": {"type": "STRING"},
            "link": {"type": "STRING"},
            "riassunto": {"type": "STRING"}
        },
        "required": ["titolo_lavoro", "organizzazione", "luogo"]
    }
}

# --- 4. FUNZIONE RICERCA ---
def cerca_lavoro_ai(profilo, keywords, paese):
    # Configurazione specifica per JSON mode
    generation_config = {
        "temperature": 0.5,
        "response_mime_type": "application/json",
        "response_schema": response_schema,
    }

    # Tentiamo prima con Flash, se fallisce fallback su Pro
    model_name = "gemini-1.5-flash"
    
    st.info(f"Tentativo con modello: {model_name}")

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )

        prompt = f"""
        Sei un recruiter esperto.
        Profilo candidato: {profilo[:3000]}
        
        Obiettivo: Trova 5 job roles ideali per: "{keywords}" in "{paese}".
        
        IMPORTANTE:
        1. Inventa/Simula 5 opportunità realistiche basate su organizzazioni reali (es. ONU, FAO, Save the Children) che operano in quell'area.
        2. Restituisci SOLO un array JSON valido.
        """

        response = model.generate_content(prompt)
        return json.loads(response.text)

    except Exception as e:
        st.error(f"Errore API: {e}")
        return None

# --- 5. INTERFACCIA ---
st.sidebar.header("Carica CV")
uploaded_files = st.sidebar.file_uploader("PDF", type="pdf", accept_multiple_files=True)
profile_text = ""

if uploaded_files:
    for f in uploaded_files:
        try:
            reader = PdfReader(f)
            for page in reader.pages:
                profile_text += page.extract_text() + "\n"
        except:
            pass
    st.sidebar.success(f"Caricati {len(profile_text)} caratteri")

col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo", "Project Manager")
with col2: ps = st.text_input("Paese", "Kenya")

if st.button("🚀 CERCA", type="primary"):
    if not GEMINI_API_KEY:
        st.error("Manca API Key")
    else:
        with st.spinner("Analisi in corso..."):
            # Fallback se non c'è testo
            p_text = profile_text if profile_text else "Nessun CV caricato."
            
            data = cerca_lavoro_ai(p_text, kw, ps)
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                
                # Export Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                    
                st.download_button("Scarica Excel", buffer.getvalue(), "jobs.xlsx")
            else:
                st.warning("Nessun risultato o errore imprevisto.")
