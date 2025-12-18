import streamlit as st
import pandas as pd
import pypdf
import google.generativeai as genai
import io
from io import StringIO

# --- 1. CONFIGURAZIONE AI (Logica Lino Bandi 2) ---
# Recuperiamo la chiave dai secrets e configuriamo in modo semplice
if "GEMINI_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_KEY"])
    # Usiamo il nome più generico possibile che Google reindirizza automaticamente
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Manca la chiave GEMINI_KEY nei Secrets!")
    st.stop()

# --- 2. INTERFACCIA ---
st.set_page_config(page_title="Job Hunter AI", layout="centered")

# Stile per il bottone rosso
st.markdown("""
<style>
.stDownloadButton > button {
    background-color: #FF4B4B !important;
    color: white !important;
    font-weight: bold;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Job Hunter AI")
st.write("Analisi professionale basata su ReliefWeb, Info-Coop e UNJobs.")

# --- 3. LETTURA PDF ---
st.sidebar.header("Carica il tuo Profilo")
uploaded_files = st.sidebar.file_uploader("Upload PDF (max 5)", type="pdf", accept_multiple_files=True)

profile_text = ""
if uploaded_files:
    for file in uploaded_files[:5]:
        pdf = pypdf.PdfReader(file)
        for page in pdf.pages:
            profile_text += page.extract_text() + "\n"
    st.sidebar.success("Profilo analizzato correttamente.")

# --- 4. RICERCA ---
st.header("🔍 Parametri di Ricerca")
col1, col2 = st.columns(2)
with col1:
    ruolo = st.text_input("Ruolo:", placeholder="es. Project Manager")
with col2:
    paese = st.text_input("Paese:", placeholder="es. Kenya")

search_type = st.radio("Sorgente:", ["Siti Specifici Cooperazione", "Web Generale"], horizontal=True)

if st.button("🚀 Avvia Job Hunter", type="primary"):
    if not (ruolo and paese):
        st.warning("Inserisci ruolo e paese.")
    else:
        with st.spinner("L'IA sta leggendo gli annunci e preparando l'Excel..."):
            try:
                # Prompt ottimizzato
                prompt = f"""
                Analizza queste informazioni per un candidato della cooperazione internazionale.
                PROFILO: {profile_text[:1500]}
                RICERCA: {ruolo} in {paese}
                
                Trova 5 opportunità e restituisci SOLO una tabella CSV con separatore ';' (punto e virgola).
                Colonne: titolo lavoro; organizzazione proponente; luogo; data di inizio; deadline; contenuto proposta; requisiti; link
                """
                
                response = model.generate_content(prompt)
                testo_risposta = response.text.strip()
                
                # Pulizia blocchi di codice se presenti
                if "```" in testo_risposta:
                    testo_risposta = testo_risposta.split("```")[1].replace("csv", "").strip()
                
                # Creazione DataFrame
                df = pd.read_csv(StringIO(testo_risposta), sep=";", on_bad_lines='skip')
                
                st.write("### Risultati trovati")
                st.dataframe(df)

                # Generazione Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='JobSearch')
                
                st.markdown("---")
                st.download_button(
                    label="📥 SCARICA REPORT EXCEL (ROSSO)",
                    data=output.getvalue(),
                    file_name=f"Job_Hunter_{paese}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except Exception as e:
                st.error(f"Errore durante l'analisi: {e}")

# --- TEST ---
if st.sidebar.button("Test AI"):
    try:
        res = model.generate_content("Ciao")
        st.sidebar.write("✅ AI Funzionante!")
    except Exception as e:
        st.sidebar.error(f"Errore: {e}")
