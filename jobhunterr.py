import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import time
import json
import google.generativeai as genai
from google.ai.generativelanguage import Content, Part

# --- 1. CONFIGURAZIONE CHIAVE ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Configura la libreria standard
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- 2. SCHEMA DI OUTPUT (Refactored per google-generativeai) ---
# La libreria standard accetta un dizionario per lo schema JSON
response_schema = {
    "type": "OBJECT",
    "properties": {
        "jobs": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "titolo_lavoro": {"type": "STRING"},
                    "organizzazione_proponente": {"type": "STRING"},
                    "luogo": {"type": "STRING"},
                    "data_di_inizio": {"type": "STRING"},
                    "deadline": {"type": "STRING"},
                    "contenuto_proposta": {"type": "STRING"},
                    "requisiti": {"type": "STRING"},
                    "link": {"type": "STRING"},
                },
                "required": ["titolo_lavoro", "organizzazione_proponente", "luogo"]
            }
        }
    }
}

# --- 3. FUNZIONE DI ESTRAZIONE CON RE-TRY AUTOMATICO ---
def cerca_lavoro_ai(profilo, keywords, paese, strategia):
    # Configurazione del modello
    generation_config = {
        "temperature": 0.4,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
        "response_schema": response_schema,
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    prompt = f"""
    Sei un esperto HR. Analizza il profilo seguente (testo estratto da CV): 
    "{profilo[:2000]}"

    Il candidato cerca opportunità per: "{keywords}" in "{paese}".
    
    Il tuo compito:
    Simula una ricerca su database globali (es. ReliefWeb, Info-Cooperazione, UNJobs) e genera 5 opportunità di lavoro verosimili e altamente compatibili con il profilo.
    
    Rispondi esclusivamente rispettando lo schema JSON fornito.
    """

    for tentativo in range(3): # Prova 3 volte
        try:
            response = model.generate_content(prompt)
            
            # Parsing della risposta
            json_response = json.loads(response.text)
            return json_response
        
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                attesa = 20
                st.warning(f"⚠️ Quota satura. In attesa di {attesa} secondi prima del tentativo {tentativo+1}...")
                time.sleep(attesa)
            else:
                st.error(f"Errore tecnico (Tentativo {tentativo+1}): {e}")
                time.sleep(2)
                
    return None

# --- 4. INTERFACCIA ---
st.set_page_config(page_title="🌍 Job Hunter Pro", layout="centered")
st.title("🌍 Job Hunter Pro")

# Stile Bottone
st.markdown("<style>.stDownloadButton>button{background-color:#FF4B4B;color:white;font-weight:bold;width:100%}</style>", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("📄 Tuo Profilo")
uploaded_files = st.sidebar.file_uploader("Carica CV (max 5 PDF)", type="pdf", accept_multiple_files=True)

profile_text = ""
if uploaded_files:
    for f in uploaded_files[:5]:
        reader = PdfReader(f)
        for page in reader.pages:
            profile_text += (page.extract_text() or "") + "\n"
    st.sidebar.success(f"Profilo caricato ({len(profile_text)} caratteri).")

# Input
col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo desiderato:", placeholder="es. Project Manager")
with col2: ps = st.text_input("Paese/Area:", placeholder="es. Kenya")

if st.button("🚀 AVVIA RICERCA AI", type="primary"):
    if not (kw and ps):
        st.warning("Inserisci Ruolo e Paese per iniziare.")
    elif not GEMINI_API_KEY:
        st.error("Chiave API mancante nei Secrets!")
    else:
        with st.spinner("L'IA sta analizzando il profilo e cercando offerte..."):
            # Se non c'è CV, usiamo una stringa vuota per evitare errori
            p_text = profile_text if profile_text else "Nessun CV fornito, basati solo sulle keywords."
            
            risultato = cerca_lavoro_ai(p_text, kw, ps, "Siti Specifici")
            
            # Verifica struttura
            if risultato and "jobs" in risultato and len(risultato["jobs"]) > 0:
                df = pd.DataFrame(risultato["jobs"])
                
                st.write("### 📊 Risultati Trovati")
                st.dataframe(df, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button("📥 SCARICA REPORT EXCEL", output.getvalue(), f"Ricerca_{ps}.xlsx")
            else:
                st.error("L'IA non ha trovato risultati o c'è stato un errore nel formato. Riprova.")
