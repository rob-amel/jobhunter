import streamlit as st
import pandas as pd
import pypdf
import google.generativeai as genai
import urllib.parse
import io
import time
from io import StringIO

# --- 1. CONFIGURAZIONE AI (VERSIONE PRO GRATUITA) ---
def initialize_ai():
    if "GEMINI_KEY" not in st.secrets:
        st.error("❌ Errore: 'GEMINI_KEY' non trovata nei Secrets.")
        st.stop()
    
    api_key = st.secrets["GEMINI_KEY"]
    genai.configure(api_key=api_key)
    
    # Passiamo a gemini-pro: è gratuito tramite API e molto più stabile per evitare il 404
    return genai.GenerativeModel('gemini-pro')

model = initialize_ai()

# --- 2. INTERFACCIA E STILE ---
st.set_page_config(page_title="🌍 Job Hunter AI Pro", layout="centered")

st.markdown("""
<style>
.stDownloadButton > button {
    background-color: #FF4B4B !important;
    color: white !important;
    font-weight: bold;
    width: 100%;
    border-radius: 10px;
    height: 3em;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI Pro")
st.subheader("Cerca lavoro nella cooperazione con l'IA (Modello Pro)")
st.markdown("---")

# --- 3. CARICAMENTO PROFILO ---
st.header("📄 1. Il tuo Profilo")
uploaded_files = st.file_uploader("Carica fino a 5 PDF (CV, Lettere, Bio)", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    with st.status("Analisi documenti in corso...") as status:
        for file in uploaded_files[:5]:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    profile_context += text + "\n"
        status.update(label="✅ Profilo caricato correttamente!", state="complete")

# --- 4. PARAMETRI DI RICERCA ---
st.header("🔍 2. Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Ruolo:", placeholder="es. Project Manager")
with col2:
    country = st.text_input("Paese:", placeholder="es. Lebanon o Remote")

search_strategy = st.radio(
    "Fonte:",
    ["Siti Specifici (ReliefWeb, Info-Coop, UNJobs)", "Tutto il Web"],
    horizontal=True
)

st.markdown("---")

# --- 5. LOGICA DI ANALISI ---
if st.button("🚀 Avvia Ricerca AI", type="primary"):
    if not (keywords and country):
        st.warning("⚠️ Inserisci parole chiave e paese.")
    else:
        progress_bar = st.progress(0)
        
        try:
            progress_bar.progress(20)
            search_query = f"{keywords} in {country}"
            
            # Prompt per Gemini Pro
            prompt = f"""
            Candidato: {profile_context[:2000]}
            Ruolo cercato: {search_query}
            Siti di riferimento: {search_strategy}

            Estrai 5 opportunità di lavoro pertinenti.
            IMPORTANTE: Rispondi SOLO in formato CSV usando il punto e virgola ';' come separatore.
            Colonne: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
            """

            progress_bar.progress(50)
            response = model.generate_content(prompt)
            
            # Parsing sicuro del testo
            res_text = response.text.strip()
            if "```csv" in res_text:
                res_text = res_text.split("```csv")[1].split("```")[0]
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0]
            
            progress_bar.progress(80)
            
            df = pd.read_csv(StringIO(res_text), sep=";", on_bad_lines='skip')
            
            st.write("### 📊 Opportunità individuate")
            st.dataframe(df, use_container_width=True)

            # --- 6. EXCEL ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Lavoro')
            
            progress_bar.progress(100)
            
            st.markdown("---")
            st.download_button(
                label="📥 SCARICA REPORT EXCEL (ROSSO)",
                data=output.getvalue(),
                file_name=f"Job_Search_{country}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Errore: {e}")
            st.info("Se l'IA non risponde correttamente, riprova tra pochi secondi (quota gratuita API).")

# --- SIDEBAR DIAGNOSTICA ---
st.sidebar.title("🛠️ Pannello di Controllo")
if st.sidebar.button("Verifica Stato AI"):
    try:
        test_resp = model.generate_content("Ping", generation_config={"max_output_tokens": 2})
        st.sidebar.success("✅ Gemini Pro è Online e Gratuito!")
    except Exception as e:
        st.sidebar.error(f"Connessione fallita: {e}")
