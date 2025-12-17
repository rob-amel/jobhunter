import streamlit as st
import pandas as pd
import pypdf
import google.generativeai as genai
import io
from io import StringIO

# --- 1. CONFIGURAZIONE AI CON AUTO-DETECTION ---
def get_available_model():
    if "GEMINI_KEY" not in st.secrets:
        st.error("❌ Manca 'GEMINI_KEY' nei Secrets.")
        st.stop()
    
    genai.configure(api_key=st.secrets["GEMINI_KEY"])
    
    try:
        # Elenca i modelli disponibili per la tua chiave
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Cerchiamo preferibilmente flash o pro
        for target in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if target in models:
                return genai.GenerativeModel(target)
        # Se non trova i preferiti, prende il primo disponibile
        return genai.GenerativeModel(models[0])
    except Exception as e:
        st.error(f"Impossibile elencare i modelli: {e}")
        st.stop()

# Inizializzazione modello
model = get_available_model()

# --- 2. INTERFACCIA ---
st.set_page_config(page_title="Job Hunter AI", layout="centered")
st.markdown("<style>.stDownloadButton>button{background-color:#FF4B4B;color:white;width:100%}</style>", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI Pro")
st.write(f"🤖 Modello attivo: `{model.model_name}`")

# --- 3. CARICAMENTO PROFILO ---
uploaded_files = st.file_uploader("Carica CV (PDF)", type="pdf", accept_multiple_files=True)
profile_context = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            profile_context += page.extract_text() + "\n"
    st.success("Profilo caricato.")

# --- 4. RICERCA ---
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Ruolo:")
with col2:
    country = st.text_input("Paese:")

if st.button("🚀 Avvia Ricerca", type="primary"):
    if keywords and country:
        with st.spinner("L'IA sta estraendo i dati..."):
            try:
                prompt = f"""
                Candidato: {profile_context[:1500]}
                Ricerca: {keywords} in {country}
                Siti: ReliefWeb, Info-Cooperazione, UNJobs.
                
                Rispondi SOLO con un CSV (punto e virgola ';').
                Colonne: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
                """
                
                response = model.generate_content(prompt)
                res_text = response.text.strip()
                
                # Pulizia blocchi di codice
                if "```" in res_text:
                    res_text = res_text.split("```")[1].replace("csv", "").strip()
                
                df = pd.read_csv(StringIO(res_text), sep=";", on_bad_lines='skip')
                st.dataframe(df)

                # Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button("📥 SCARICA EXCEL", output.getvalue(), f"Jobs_{country}.xlsx")
            except Exception as e:
                st.error(f"Errore: {e}")
    else:
        st.warning("Riempi i campi.")
