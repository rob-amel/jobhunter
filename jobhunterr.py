import streamlit as st
import pandas as pd
from pypdf import PdfReader
import io
import os
import json
import google.generativeai as genai
from jobspy import scrape_jobs

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Job Hunter Pro - Opportunità Pertinenti", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def ottieni_modello_valido():
    try:
        modelli = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if p in modelli: return p
        return modelli[0] if modelli else None
    except: return None

def analizza_e_trova_offerte(testo_documenti, keywords, paese):
    model_name = ottieni_modello_valido()
    if not model_name: return None

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.7, "response_mime_type": "application/json"} # Temp più alta per maggiore pertinenza
        )

        prompt = f"""
        TASK:
        1. Analizza i documenti del candidato: {testo_documenti[:8000]}
        2. Determina la sua anzianità lavorativa effettiva (anni totali).
        3. Trova 5-7 opportunità in "{paese}" che siano PERTINENTI a "{keywords}". 
        
        LOGICA DI PERTINENZA (NON ESATTA):
        - Includi ruoli affini (es. se cerca "Project Manager", considera anche "Program Coordinator", "Operations Officer" o "Team Lead").
        - Valuta il settore: se il CV è orientato al non-profit, cerca in ONG e Organizzazioni Internazionali.
        - RISPETTA IL LIVELLO: Se il candidato ha 4 anni di esperienza, proponi ruoli "Intermediate" o "Junior-Mid", evitando "Senior/Director" da 10+ anni.
        - Sii creativo: se non trovi offerte identiche, proponi ruoli dove le sue competenze trasversali sono un valore aggiunto.

        RESTITUISCI SOLO JSON:
        {{
          "match_offerte": [
            {{
              "titolo": "...",
              "organizzazione": "...",
              "perche_pertinente": "Spiega il nesso logico tra il CV e questa posizione anche se non è un match esatto",
              "anni_richiesti": "...",
              "competenze_chiave_richieste": "...",
              "link_ricerca_diretta": "URL di ricerca specifica su LinkedIn/Google per questa posizione"
            }}
          ]
        }}
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:-3]
        return json.loads(text)
    except: return None

# --- INTERFACCIA ---
st.title("🌍 Job Hunter Pro")
st.markdown("##### Ricerca intelligente di opportunità pertinenti basata sui tuoi documenti")

with st.sidebar:
    st.header("📂 Caricamento")
    uploaded_files = st.file_uploader("Carica CV e Certificati (PDF)", type="pdf", accept_multiple_files=True)
    profile_text = ""
    if uploaded_files:
        for f in uploaded_files:
            reader = PdfReader(f)
            for page in reader.pages:
                profile_text += (page.extract_text() or "") + "\n"

col1, col2 = st.columns(2)
with col1: kw = st.text_input("Ruolo/Settore desiderato")
with col2: ps = st.text_input("Area Geografica")

if st.button("🚀 TROVA OPPORTUNITÀ PERTINENTI", type="primary"):
    if not profile_text:
        st.warning("Carica i tuoi documenti per iniziare.")
    elif not (kw and ps):
        st.warning("Inserisci cosa cerchi e dove.")
    else:
        with st.spinner("L'IA sta scansionando il mercato per opportunità affini..."):
            risultato = analizza_e_trova_offerte(profile_text, kw, ps)
            
            if risultato and 'match_offerte' in risultato:
                st.subheader(f"🔍 Offerte individuate in {ps}")
                
                for item in risultato['match_offerte']:
                    with st.container():
                        st.markdown(f"### 📌 {item['titolo']}")
                        st.markdown(f"**🏢 Organizzazione:** {item['organizzazione']} | **⏳ Exp. Richiesta:** {item['anni_richiesti']}")
                        
                        # Box evidenziato per la pertinenza
                        st.info(f"**💡 Logica di Pertinenza:** {item['perche_pertinente']}")
                        
                        st.write(f"**🛠 Competenze chiave:** {item['competenze_chiave_richieste']}")
                        st.markdown(f"[🔗 Vai all'offerta o cerca su LinkedIn]({item['link_ricerca_diretta']})")
                        st.divider()

                # Excel Export
                df_export = pd.DataFrame(risultato['match_offerte'])
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, index=False)
                st.download_button("📥 Scarica Report Excel", buffer.getvalue(), "lavori_pertinenti.xlsx")
            else:
                st.error("Nessun risultato trovato. Prova ad ampliare l'area geografica o il ruolo.")
