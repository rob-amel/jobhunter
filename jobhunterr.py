import streamlit as st
import pandas as pd
import pypdf
import io
import os
import time
from io import BytesIO, StringIO
from google import genai

# --- 1. RECUPERO CHIAVE API ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- 2. CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="🌍 Job Hunter AI Pro", layout="centered")

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

# --- 3. SIDEBAR: CARICAMENTO PROFILO ---
st.sidebar.header("📄 Il tuo Profilo")
uploaded_files = st.sidebar.file_uploader("Carica fino a 5 PDF", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text = page.extract_text()
            if text: profile_context += text + "\n"
    st.sidebar.success(f"✅ Profilo pronto!")

# --- 4. PARAMETRI DI RICERCA ---
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Ruolo:", placeholder="es. Project Manager")
with col2:
    country = st.text_input("Paese:", placeholder="es. Sudan")

search_strategy = st.radio("Sorgente:", ["Siti Specifici (ReliefWeb, Info-Coop, UNJobs)", "Tutto il Web"], horizontal=True)

# --- 5. FUNZIONE DI ANALISI (VERSIONE STABILE V1) ---
def cerca_lavoro_ai(profilo, query, strategia):
    if not GEMINI_API_KEY:
        st.error("❌ Manca la API Key nei Secrets.")
        return None

    # Inizializziamo il client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Sei un esperto HR internazionale. Trova 5 opportunità di lavoro per questa ricerca:
    PROFILO: {profilo[:1500]}
    RICERCA: {query} su {strategia}
    
    Rispondi SOLO in formato CSV usando il punto e virgola ';' come separatore.
    titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
    """

    for tentativo in range(3):
        try:
            # FORZIAMO IL MODELLO SENZA PREFISSI E USANDO LA VERSIONE STABILE
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt
            )
            
            text_out = response.text.strip()
            if "```" in text_out:
                text_out = text_out.split("```")[1].replace("csv", "").strip()
            
            return pd.read_csv(StringIO(text_out), sep=";", on_bad_lines='skip')

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                st.warning("Quota esaurita, attendo 15 secondi...")
                time.sleep(15)
            elif "404" in err_msg:
                # Se fallisce con 1.5-flash, proviamo l'ultimo tentativo con gemini-pro
                st.warning("Modello flash non trovato, provo gemini-pro...")
                try:
                    response = client.models.generate_content(model='gemini-pro', contents=prompt)
                    # ... logica di parsing identica ...
                    return pd.read_csv(StringIO(response.text.strip().replace("```csv", "").replace("```", "").strip()), sep=";")
                except:
                    st.error("Errore di compatibilità modelli Google.")
                    break
            else:
                st.error(f"❌ Errore: {e}")
                break
    return None

# --- 6. ESECUZIONE ---
if st.button("🚀 AVVIA JOB HUNTER", type="primary"):
    if not (keywords and country):
        st.warning("Compila i campi ruolo e paese.")
    else:
        with st.spinner("L'IA sta lavorando..."):
            df = cerca_lavoro_ai(profile_context, f"{keywords} {country}", search_strategy)
            if df is not None:
                st.dataframe(df, use_container_width=True)
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False, engine='xlsxwriter')
                st.download_button("📥 SCARICA EXCEL (ROSSO)", excel_buffer.getvalue(), f"Jobs_{country}.xlsx")
