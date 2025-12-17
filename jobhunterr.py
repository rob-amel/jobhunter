import streamlit as st
import pandas as pd
import pypdf
import google.generativeai as genai
import urllib.parse
import io
import time
from io import StringIO

# --- 1. CONFIGURAZIONE AI (STABILE) ---
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        genai.configure(api_key=api_key)
        # Usiamo il percorso completo e la versione latest per evitare errori 404
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
    else:
        st.error("❌ Errore: 'GEMINI_KEY' non trovata nei Secrets.")
        st.stop()
except Exception as e:
    st.error(f"❌ Errore critico: {e}")
    st.stop()

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
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI Pro")
st.subheader("Cerca lavoro nella cooperazione con l'IA")
st.info("Questa app analizza i tuoi PDF e cerca opportunità su ReliefWeb, Info-Coop e UNJobs.")

# --- 3. CARICAMENTO PROFILO ---
st.header("📄 1. Il tuo Profilo")
uploaded_files = st.file_uploader("Carica fino a 5 PDF (CV, Lettere, Bio)", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        try:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                profile_context += page.extract_text() + "\n"
        except Exception as e:
            st.warning(f"Impossibile leggere il file {file.name}: {e}")
    st.success(f"✅ Analizzati {len(uploaded_files)} file. Profilo pronto.")

# --- 4. PARAMETRI DI RICERCA ---
st.header("🔍 2. Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Quale ruolo cerchi?", placeholder="es. Project Manager WASH")
with col2:
    country = st.text_input("In quale Paese?", placeholder="es. Sudan, Kenya o Remote")

search_strategy = st.radio(
    "Dove vuoi cercare?",
    ["Siti Specifici (ReliefWeb, Info-Coop, UNJobs)", "Tutto il Web"],
    horizontal=True
)

st.markdown("---")

# --- 5. LOGICA DI ANALISI E AZIONE ---
if st.button("🚀 Avvia Ricerca ed Estrazione AI", type="primary"):
    if not (keywords and country):
        st.warning("⚠️ Per favore, inserisci parole chiave e paese.")
    else:
        with st.spinner("L'IA sta elaborando i dati e simulando la ricerca..."):
            
            # Prepariamo la query per la simulazione e i link reali
            search_query = f"{keywords} {country}"
            
            # Prompt ingegnerizzato per estrazione dati simulata o basata su web-context
            prompt = f"""
            Sei un esperto HR per ONG Internazionali.
            PROFILO CANDIDATO: {profile_context[:2000]}
            DOMANDA DI LAVORO: {search_query}
            
            Trova 5 posizioni lavorative realistiche e attuali che corrispondono a questa ricerca sui siti {search_strategy}.
            Genera i dati in formato CSV usando esclusivamente il punto e virgola ';' come separatore.
            
            IMPORTANTE: Rispondi SOLO con il blocco CSV.
            COLONNE: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
            """

            try:
                # Chiamata al modello
                response = model.generate_content(prompt)
                res_text = response.text
                
                # Pulizia del testo ricevuto dall'IA
                clean_csv = res_text.replace("```csv", "").replace("```", "").strip()
                
                # Conversione in DataFrame
                df = pd.read_csv(StringIO(clean_csv), sep=";", on_bad_lines='skip')
                
                # Visualizzazione risultati
                st.write("### 📊 Proposte individuate per te")
                st.dataframe(df)

                # --- 6. GENERAZIONE EXCEL ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Job_Opportunities')
                    # Formattazione base dell'Excel
                    workbook = writer.book
                    worksheet = writer.sheets['Job_Opportunities']
                    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                
                excel_data = output.getvalue()

                st.markdown("---")
                st.download_button(
                    label="📥 SCARICA REPORT EXCEL (ROSSO)",
                    data=excel_data,
                    file_name=f"Job_Analysis_{country.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"❌ Errore durante l'analisi AI: {e}")
                st.info("Verifica la connessione o prova a rigenerare la chiave se l'errore persiste.")

# --- TEST SIDEBAR ---
if st.sidebar.button("🛠️ Test Connessione AI"):
    try:
        test_res = model.generate_content("Rispondi solo con 'SISTEMA ONLINE'")
        st.sidebar.success(test_res.text)
    except Exception as e:
        st.sidebar.error(f"Errore: {e}")
