import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import time
from datetime import datetime
from google import genai
from google.genai import types

# --- 1. CONFIGURAZIONE CHIAVE ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- 2. SCHEMA DI OUTPUT (STRUTTURA LINO BANDI) ---
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

# --- 3. FUNZIONE DI ESTRAZIONE CON RE-TRY AUTOMATICO ---
def cerca_lavoro_ai(profilo, keywords, paese, strategia):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Sei un esperto HR. Analizza il profilo: {profilo[:1500]}
    Trova 5 opportunità per: {keywords} in {paese}.
    Sorgenti: ReliefWeb, Info-Cooperazione, UNJobs.
    Rispondi esclusivamente in formato JSON come da schema.
    """

    for tentativo in range(3): # Prova 3 volte prima di arrendersi
        try:
            # CAMBIATO A 1.5-FLASH PER EVITARE IL LIMIT 0
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=output_schema,
                ),
            )
            return response.parsed
        
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                attesa = 20 # Secondi di attesa cautelativa
                st.warning(f"⚠️ Quota satura. In attesa di {attesa} secondi prima del tentativo {tentativo+1}...")
                time.sleep(attesa)
            else:
                st.error(f"Errore tecnico: {e}")
                return None
    return None

# --- 4. INTERFACCIA ---
st.set_page_config(page_title="🌍 Job Hunter Pro", layout="centered")
st.title("🌍 Job Hunter Pro")

# Stile Bottone Rosso
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
    st.sidebar.success("Profilo caricato.")

# Input
col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo desiderato:")
with col2: ps = st.text_input("Paese/Area:")

if st.button("🚀 AVVIA RICERCA AI", type="primary"):
    if not (kw and ps):
        st.warning("Inserisci i dati per la ricerca.")
    elif not GEMINI_API_KEY:
        st.error("Chiave API mancante nei Secrets!")
    else:
        with st.spinner("L'IA sta elaborando le migliori offerte per te..."):
            risultato = cerca_lavoro_ai(profile_text, kw, ps, "Siti Specifici")
            
            if risultato and hasattr(risultato, 'jobs'):
                df = pd.DataFrame(risultato.jobs)
                st.write("### 📊 Risultati Trovati")
                st.dataframe(df, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button("📥 SCARICA REPORT EXCEL", output.getvalue(), f"Ricerca_{ps}.xlsx")
            else:
                st.error("Non è stato possibile recuperare dati. Riprova tra un minuto.")
