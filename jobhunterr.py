import streamlit as st
import pandas as pd
import pypdf
import io
import os
from io import BytesIO, StringIO
from google import genai

# --- 1. RECUPERO CHIAVE API (METODO LINO BANDI 2) ---
try:
    # Cerchiamo nei Secrets di Streamlit
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    # Se non presente (test locale), cerchiamo nelle variabili d'ambiente
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- 2. CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="🌍 Job Hunter AI Pro", layout="centered")

# Stile per il bottone rosso richiesto
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
st.markdown("Analizza il tuo profilo e trova lavoro nei siti della cooperazione.")

# --- 3. SIDEBAR: CARICAMENTO PROFILO ---
st.sidebar.header("📄 Il tuo Profilo")
uploaded_files = st.sidebar.file_uploader("Carica fino a 5 PDF (CV/Bio)", type="pdf", accept_multiple_files=True)

profile_context = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                profile_context += text + "\n"
    st.sidebar.success(f"✅ {len(uploaded_files)} file analizzati!")

# --- 4. PARAMETRI DI RICERCA ---
st.header("🔍 Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Ruolo:", placeholder="es. Project Manager WASH")
with col2:
    country = st.text_input("Paese:", placeholder="es. Sudan o Remote")

search_strategy = st.radio("Sorgente dati:", ["Siti Specifici (ReliefWeb, Info-Coop, UNJobs)", "Tutto il Web"], horizontal=True)

# --- 5. FUNZIONE DI ANALISI (CORRETTA) ---
def cerca_lavoro_ai(profilo, query, strategia):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "":
        st.error("❌ Errore: API Key mancante. Inseriscila nei Secrets di Streamlit.")
        return None

    try:
        # Passiamo esplicitamente la chiave al Client (risolve l'errore 'Missing key inputs')
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        Sei un esperto HR internazionale. Analizza il profilo del candidato e la sua ricerca.
        PROFILO CANDIDATO: {profilo[:2500]}
        RICERCA: {query} su {strategia}
        
        Trova 5 opportunità di lavoro reali o verosimili. 
        Rispondi SOLO in formato CSV usando il punto e virgola ';' come separatore.
        Colonne: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
        """
        
        # Chiamata al modello 2.0 Flash (veloce e gratuito)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        text_out = response.text.strip()
        
        # Pulizia blocchi di codice markdown
        if "```" in text_out:
            text_out = text_out.split("```")[1].replace("csv", "").strip()
        
        # Trasformazione in DataFrame
        df = pd.read_csv(StringIO(text_out), sep=";", on_bad_lines='skip')
        return df

    except Exception as e:
        st.error(f"❌ Errore durante la chiamata AI: {e}")
        return None

# --- 6. ESECUZIONE ---
if st.button("🚀 AVVIA JOB HUNTER", type="primary"):
    if not (keywords and country):
        st.warning("⚠️ Inserisci ruolo e paese per iniziare.")
    else:
        with st.spinner("L'IA sta elaborando i dati..."):
            df_risultati = cerca_lavoro_ai(profile_context, f"{keywords} {country}", search_strategy)
            
            if df_risultati is not None and not df_risultati.empty:
                st.write("### 📊 Risultati per la tua ricerca")
                st.dataframe(df_risultati, use_container_width=True)
                
                # Creazione Excel
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_risultati.to_excel(writer, index=False, sheet_name='JobSearch')
                
                st.markdown("---")
                st.download_button(
                    label="📥 SCARICA REPORT EXCEL (ROSSO)",
                    data=excel_buffer.getvalue(),
                    file_name=f"Job_Opportunities_{country}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Nessun risultato generato. Riprova tra un momento.")
