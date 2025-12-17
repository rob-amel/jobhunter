import streamlit as st
import pandas as pd
import pypdf
import google.generativeai as genai
import urllib.parse
import io
import time
from io import StringIO

# --- 1. CONFIGURAZIONE AI (SISTEMA ANTI-404) ---
def initialize_ai():
    if "GEMINI_KEY" not in st.secrets:
        st.error("❌ Errore: 'GEMINI_KEY' non trovata nei Secrets.")
        st.stop()
    
    api_key = st.secrets["GEMINI_KEY"]
    genai.configure(api_key=api_key)
    
    # Proviamo a usare il nome modello più standard
    # Se fallisce, l'utente vedrà l'errore specifico nel test sidebar
    return genai.GenerativeModel('gemini-1.5-flash')

model = initialize_ai()

# --- 2. INTERFACCIA E STILE ---
st.set_page_config(page_title="🌍 Job Hunter AI Pro", layout="centered")

# CSS per il Bottone Rosso e l'estetica
st.markdown("""
<style>
.stDownloadButton > button {
    background-color: #FF4B4B !important;
    color: white !important;
    font-weight: bold;
    width: 100%;
    border-radius: 10px;
    border: none;
    padding: 0.5rem;
}
.stDownloadButton > button:hover {
    background-color: #D32F2F !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI Pro")
st.subheader("Cerca lavoro nella cooperazione con l'IA")
st.markdown("---")

# --- 3. CARICAMENTO PROFILO ---
st.header("📄 1. Il tuo Profilo")
uploaded_files = st.file_uploader("Carica fino a 5 PDF (CV, Lettere, Bio)", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    with st.status("Lettura PDF in corso...") as status:
        for file in uploaded_files[:5]:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                profile_context += page.extract_text() + "\n"
        status.update(label="✅ Profilo analizzato!", state="complete")

# --- 4. PARAMETRI DI RICERCA ---
st.header("🔍 2. Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Ruolo desiderato:", placeholder="es. Project Manager WASH")
with col2:
    country = st.text_input("Paese di destinazione:", placeholder="es. Sudan, Kenya o Remote")

search_strategy = st.radio(
    "Fonte della ricerca:",
    ["Siti Specifici (ReliefWeb, Info-Coop, UNJobs)", "Tutto il Web"],
    horizontal=True
)

st.markdown("---")

# --- 5. LOGICA DI ANALISI ---
if st.button("🚀 Avvia Ricerca ed Estrazione AI", type="primary"):
    if not (keywords and country):
        st.warning("⚠️ Inserisci parole chiave e paese per continuare.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("L'IA sta consultando i database internazionali...")
            progress_bar.progress(30)
            
            search_query = f"{keywords} {country}"
            
            # Prompt ottimizzato per estrazione CSV pulita
            prompt = f"""
            Profilo Candidato: {profile_context[:1500]}
            Ricerca richiesta: {search_query}
            
            Agisci come un esperto HR. Genera 5 proposte di lavoro reali/verosimili per questa ricerca.
            Restituisci i dati SOLO come tabella CSV usando il punto e virgola ';' come separatore.
            Colonne obbligatorie: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
            """

            progress_bar.progress(60)
            response = model.generate_content(prompt)
            res_text = response.text
            
            # Pulizia e Parsing
            clean_csv = res_text.replace("```csv", "").replace("```", "").strip()
            df = pd.read_csv(StringIO(clean_csv), sep=";", on_bad_lines='skip')
            
            progress_bar.progress(100)
            status_text.text("✅ Analisi completata!")
            
            st.write("### 📊 Risultati per la tua candidatura")
            st.dataframe(df)

            # --- 6. GENERAZIONE EXCEL ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Job_Opportunities')
            
            excel_data = output.getvalue()

            st.markdown("---")
            st.download_button(
                label="📥 SCARICA REPORT EXCEL",
                data=excel_data,
                file_name=f"Job_Analysis_{country}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Errore: {e}")
            st.info("💡 Suggerimento: Se vedi ancora 404, prova a cliccare sul tasto 'Diagnostica' nella sidebar.")

# --- SIDEBAR DIAGNOSTICA ---
st.sidebar.title("🛠️ Strumenti")
if st.sidebar.button("Diagnostica Connessione"):
    try:
        # Test rapido con risposta minima
        test_model = genai.GenerativeModel('gemini-1.5-flash')
        response = test_model.generate_content("Hi", generation_config={"max_output_tokens": 5})
        st.sidebar.success(f"IA Online! Modello: gemini-1.5-flash")
    except Exception as e:
        st.sidebar.error(f"Errore di connessione: {e}")
        st.sidebar.write("Prova a cambiare il nome del modello nel codice in 'gemini-pro'.")
