import streamlit as st
import pandas as pd
import pypdf
import google.generativeai as genai
import urllib.parse
import io
import time

# --- CONFIGURAZIONE AI (RECUPERO SECRETS) ---
try:
    # Cerchiamo la chiave nei secrets di Streamlit
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        genai.configure(api_key=api_key)
        # Inizializziamo il modello
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("❌ Errore: 'GEMINI_KEY' non trovata nei Secrets di Streamlit.")
        st.stop()
except Exception as e:
    st.error(f"❌ Errore critico di configurazione: {e}")
    st.stop()

# --- STILE ---
st.set_page_config(page_title="🌍 Job Hunter AI Pro", layout="centered")
st.markdown("""
<style>
.stDownloadButton > button { background-color: #FF4B4B !important; color: white !important; font-weight: bold; width: 100%; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI Pro")
st.markdown("---")

# 1. CARICAMENTO PROFILO
st.header("📄 1. Il tuo Profilo")
uploaded_files = st.file_uploader("Carica fino a 5 PDF (CV, Lettere, Bio)", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            profile_context += page.extract_text() + "\n"
    st.success(f"Analizzati {len(uploaded_files)} file.")

# 2. PARAMETRI DI RICERCA
st.header("🔍 2. Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Parole Chiave:", placeholder="es. Project Manager WASH")
with col2:
    country = st.text_input("Paese:", placeholder="es. Sudan o Remote")

search_strategy = st.radio("Strategia:", ["Siti Specifici", "Tutto il Web"], horizontal=True)

# 3. RICERCA E ANALISI
if st.button("🚀 Avvia Ricerca AI", type="primary"):
    if not (keywords and country):
        st.warning("Inserisci i dati richiesti.")
    else:
        with st.spinner("L'IA sta elaborando i dati..."):
            search_query = f"{keywords} {country}"
            
            # Prompt ingegnerizzato per ottenere dati strutturati puliti
            prompt = f"""
            Agisci come un esperto di recruiting nella cooperazione internazionale. 
            Candidato: {profile_context[:1500]}
            Ricerca attuale: {search_query} on {search_strategy}.
            
            Genera 3 opportunità di lavoro realistiche. 
            Rispondi esclusivamente con una tabella CSV usando il punto e virgola ';' come separatore.
            Colonne: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
            """
            
            try:
                # Esecuzione chiamata AI
                response = model.generate_content(prompt)
                res_text = response.text
                
                # Parsing dei dati (trasformiamo il CSV testuale in DataFrame)
                from io import StringIO
                # Pulizia per rimuovere eventuali blocchi di codice markdown (```csv ...)
                clean_text = res_text.replace("```csv", "").replace("```", "").strip()
                df = pd.read_csv(StringIO(clean_text), sep=";")
                
                st.write("### 📊 Risultati Trovati")
                st.dataframe(df)

                # 4. EXCEL DOWNLOAD
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Job_Search')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 SCARICA REPORT EXCEL",
                    data=excel_data,
                    file_name=f"Job_Search_{country}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Errore durante l'analisi: {e}")
                st.info("Suggerimento: Verifica che la tua chiave API non abbia restrizioni di regione o di quota.")
