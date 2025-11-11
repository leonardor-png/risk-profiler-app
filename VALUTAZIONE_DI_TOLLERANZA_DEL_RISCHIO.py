# -*- coding: utf-8 -*-
"""
Created on Fri Nov  7 18:45:16 2025

@author: leona
"""
#pip install streamlit
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO 
import os 
import openpyxl 
from openpyxl.drawing.image import Image as OpenpyxlImage 

# ==============================================================================
# 1. CLASSI E DATI DI RIFERIMENTO
# ==============================================================================

class ClientData:
    """Contenitore per i dati di un singolo cliente e il suo profilo di rischio."""
    def __init__(self, name, score, profile, allocation, details, description, desired_profile, justification):
        self.DataOra = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.NomeCliente = name
        self.PunteggioTotale = score
        self.ProfiloRischio = profile
        self.AllocazioneSuggerita = allocation
        self.PunteggiDettaglio = details
        self.DescrizioneProfilo = description
        self.ProfiloDesiderato = desired_profile
        self.Giustificazione = justification

    def to_dataframe(self):
        """Converte i dati del cliente in un DataFrame Pandas per lo storico."""
        data = {
            'Data_Ora': [self.DataOra],
            'Nome_Cliente': [self.NomeCliente],
            'Punteggio_Totale': [self.PunteggioTotale],
            'Profilo_Rischio_Assegnato': [self.ProfiloRischio],
            'Profilo_Rischio_Desiderato': [self.ProfiloDesiderato],
            'Allocazione_Suggerita': [self.AllocazioneSuggerita],
            'Giustificazione_Disallineamento': [self.Giustificazione],
            'Score_Capacita_Finanziaria': [self.PunteggiDettaglio.get('Capacità Finanziaria', 0)],
            'Score_Conoscenza': [self.PunteggiDettaglio.get('Conoscenza', 0)],
            'Score_Orizzonte': [self.PunteggiDettaglio.get('Orizzonte Temporale', 0)],
            'Score_Psicologico': [self.PunteggiDettaglio.get('Tolleranza Psicologica', 0)]
        }
        return pd.DataFrame(data)

class RiskProfiler:
    """Classe principale che gestisce il questionario e l'output."""
    
    FILE_EXCEL = 'Storico_Report_Rischio.xlsx' 
    PUNTEGGIO_MAX = 100 
    
    PROFILES = {
        (0, 20): ("1. Conservatore", "Focus su preservazione del capitale, Basso rischio.", "Obbligazioni: 80% / Azioni: 20%"),
        (21, 40): ("2. Moderato", "Bilanciamento tra rendimento e protezione.", "Obbligazioni: 60% / Azioni: 40%"),
        (41, 60): ("3. Bilanciato", "Equilibrio tra crescita e conservazione.", "Obbligazioni: 50% / Azioni: 50%"),
        (61, 80): ("4. Dinamico", "Predominanza di opportunità di crescita, Rischio Elevato.", "Obbligazioni: 30% / Azioni: 70%"),
        (81, 100): ("5. Aggressivo", "Massimizzazione del rendimento, tolleranza massima al rischio.", "Obbligazioni: 10% / Azioni: 90%")
    }
    
    QUESTIONNAIRE = [
        {'area': 'Capacità Finanziaria', 'domanda': "A1. Stima del tuo Reddito Annuo Lordo (RAL)?", 'opzioni': {"< 25k €": 5, "25k € - 50k €": 10, "> 50k €": 15}},
        {'area': 'Capacità Finanziaria', 'domanda': "A2. Patrimonio investibile che sei disposto a rischiare?", 'opzioni': {"< 10%": 5, "10% - 30%": 10, "> 30%": 15}},
        {'area': 'Conoscenza', 'domanda': "B1. Quanto è vasta la tua conoscenza di prodotti complessi (es. Derivati)?", 'opzioni': {"Nessuna/Minima": 5, "Buona conoscenza": 10, "Elevata e uso regolare": 20}},
        {'area': 'Orizzonte Temporale', 'domanda': "C1. Qual è l'orizzonte temporale principale per i tuoi investimenti?", 'opzioni': {"< 3 Anni": 5, "3 - 7 Anni": 10, "> 7 Anni": 20}},
        {'area': 'Tolleranza Psicologica', 'domanda': "D1. Come reagiresti a un calo del 25% in pochi mesi?", 'opzioni': {"Venderesti subito (Panico)": 0, "Manterresti con preoccupazione": 10, "Vedresti un'opportunità di acquisto": 30}}
    ]

    def _determine_profile(self, name, score, details):
        """Assegna il profilo di rischio e applica il guardrail di coerenza."""
        profile_name = "Non Classificabile"
        allocation = "Da definire."
        description = ""
        
        for (min_s, max_s), (p_name, desc, alloc) in self.PROFILES.items():
            if min_s <= score <= max_s:
                profile_name = p_name
                description = desc
                allocation = alloc
                break
        
        profilo_iniziale = profile_name
        
        # GUARDRAIL: Controllo Capacità Finanziaria
        score_capacita = details.get('Capacità Finanziaria', 0)
        
        if score_capacita <= 15 and ("Aggressivo" in profile_name or "Dinamico" in profile_name):
            if score_capacita <= 10:
                 profile_name = self.PROFILES[(21, 40)][0] # Moderato
                 description += " [⚠ Declassato per Bassa Capacità Finanziaria (<=10/30)]."
                 allocation = self.PROFILES[(21, 40)][2]
            elif score_capacita <= 15 and "Aggressivo" in profile_name:
                 profile_name = self.PROFILES[(41, 60)][0] # Bilanciato
                 description += " [⚠ Ridimensionato per Capacità Finanziaria Media/Bassa (<=15/30)]."
                 allocation = self.PROFILES[(41, 60)][2]
            
        client_data = ClientData(name, score, profile_name, allocation, details, description, 
                                 desired_profile="N/A", justification="N/A")
        return client_data, profilo_iniziale

    def create_plot(self, client):
        """Crea la figura Matplotlib per il solo Radar Chart."""
        categories = list(client.PunteggiDettaglio.keys())
        values = list(client.PunteggiDettaglio.values())
        max_scores = [30, 20, 20, 30] 
        values_normalized = [v / m for v, m in zip(values, max_scores)]
        
        plt.style.use('default') 
        fig = plt.figure(figsize=(8, 8)) 
        
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        ax1 = fig.add_subplot(111, polar=True) 
        ax1.plot(angles, values_normalized + values_normalized[:1], linewidth=2, linestyle='solid', label=client.ProfiloRischio)
        ax1.fill(angles, values_normalized + values_normalized[:1], 'teal', alpha=0.4)
        ax1.set_xticks(angles[:-1])
        ax1.set_xticklabels(categories)
        ax1.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax1.set_yticklabels(['Basso', 'Medio-Basso', 'Medio-Alto', 'Alto'])
        ax1.set_title(f'Distribuzione Punteggi per Aree\nCliente: {client.NomeCliente}', size=14, y=1.1)
        ax1.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        
        return fig 

    def generate_excel_report(self, client, df_full):
        """Genera il file Excel in memoria (BytesIO) per il download."""
        
        timestamp_clean = client.DataOra.replace('-', '').replace(':', '').replace(' ', '').replace('.', '')
        unique_id = timestamp_clean[-10:] 
        name_clean_safe = client.NomeCliente.replace(" ", "_").replace(".", "")[:18]
        sheet_name_report = f"Rpt_{name_clean_safe}_{unique_id}" 
        sheet_name_report = sheet_name_report[:31] 

        # Genera il grafico e l'immagine
        fig = self.create_plot(client)
        img_data = BytesIO()
        fig.savefig(img_data, format='png', dpi=200, bbox_inches='tight')
        img_data.seek(0)
        img = OpenpyxlImage(img_data)
        img.width = 500
        img.height = 500

        # Crea un file Excel in memoria
        output = BytesIO()
        
        # Gestione: Se lo storico esiste, lo apri in append, altrimenti in write
        try:
            workbook = openpyxl.load_workbook(self.FILE_EXCEL)
            mode = 'a'
        except FileNotFoundError:
            workbook = openpyxl.Workbook()
            default_sheet = workbook.active
            workbook.remove(default_sheet)
            mode = 'w'
        
        # Scrittura dello Storico e del Report
        with pd.ExcelWriter(output, engine='openpyxl', mode=mode, if_sheet_exists='replace') as writer:
            writer.book = workbook
            
            # A. Scrittura dello Storico aggiornato
            df_full.to_excel(writer, sheet_name='Storico Clienti', index=False)
            
            # B. Aggiunge il nuovo foglio report
            pd.DataFrame().to_excel(writer, sheet_name=sheet_name_report, index=False)
            
            # C. Inserimento dei contenuti nel nuovo foglio
            worksheet_report = writer.book[sheet_name_report]
            
            worksheet_report.add_image(img, 'B2')

            # D. Inserisce Analisi Puntuata (Normalizzazione %)
            max_scores = [30, 20, 20, 30] 
            categories = list(client.PunteggiDettaglio.keys())
            values = list(client.PunteggiDettaglio.values())
            
            worksheet_report['G1'] = "ANALISI PUNTUALE PER AREA"
            worksheet_report['G2'] = "Area"
            worksheet_report['H2'] = "Punteggio / Max"
            worksheet_report['I2'] = "Normalizzato %"
            
            start_row = 3
            for i, category in enumerate(categories):
                max_s = max_scores[i]
                score = values[i]
                percentage = (score / max_s) * 100
                
                worksheet_report[f'G{start_row + i}'] = category
                worksheet_report[f'H{start_row + i}'] = f"{score} / {max_s}"
                worksheet_report[f'I{start_row + i}'] = f"{percentage:.1f}%"
                
            # E. Dettagli Report Principale
            worksheet_report['A1'] = f"Report di Profilazione: {client.NomeCliente}"
            worksheet_report['A3'] = f"Profilo Calcolato: {client.ProfiloRischio}"
            worksheet_report['A4'] = f"Profilo Desiderato: {client.ProfiloDesiderato}"
            worksheet_report['A5'] = f"Punteggio Totale: {client.PunteggioTotale}/{self.PUNTEGGIO_MAX}"
            worksheet_report['A6'] = f"Allocazione Suggerita: {client.AllocazioneSuggerita}"
            worksheet_report['A8'] = f"Gap Coerenza: {'DISALLINEATO' if client.ProfiloRischio != client.ProfiloDesiderato else 'ALLINEATO'}"
            worksheet_report['A9'] = f"Giustificazione: {client.Giustificazione}"
                
        output.seek(0)
        return output
    
profiler = RiskProfiler()

# ==============================================================================
# 2. INTERFACCIA STREAMLIT E LOGICA APPLICATIVA
# ==============================================================================

st.set_page_config(page_title="🛡️ Risk Profiler MiFID", layout="wide")
st.title("🛡️ Professional Risk Profiler (MiFID Structure)")

# CHIAVE: Funzione di caching aggiornata (risolve l'errore allow_output_mutation)
@st.cache_data 
def get_historical_df():
    """Carica il DataFrame storico, usa try/except in caso di file non trovato."""
    try:
        # Assicura che il file sia cercato correttamente (Streamlit è in esecuzione nella stessa directory)
        if os.path.exists(profiler.FILE_EXCEL):
            return pd.read_excel(profiler.FILE_EXCEL, sheet_name='Storico Clienti')
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# Inizializzazione dello stato di Streamlit
if 'historical_df' not in st.session_state:
    st.session_state.historical_df = get_historical_df()
    
if 'profile_results' not in st.session_state:
    st.session_state.profile_results = None

with st.form("risk_profiler_form"):
    
    st.header("1. Dati Cliente")
    name = st.text_input("Nome Cliente / ID", key='client_name', value='Nuovo Cliente')
    
    total_score = 0
    details = {'Capacità Finanziaria': 0, 'Conoscenza': 0, 'Orizzonte Temporale': 0, 'Tolleranza Psicologica': 0}
    
    st.header("2. Questionario di Profilazione")
    
    profile_options = {p[0]: p[0] for p in profiler.PROFILES.values()}
    profile_names_list = list(profile_options.keys())

    for i, q in enumerate(profiler.QUESTIONNAIRE):
        st.subheader(f"Area: {q['area']}")
        
        options_text = list(q['opzioni'].keys())
        
        choice_text = st.radio(
            q['domanda'],
            options_text,
            index=0,
            key=f'q_{i}'
        )
        
        score_value = q['opzioni'][choice_text]
        total_score += score_value
        details[q['area']] += score_value
        
    st.header("3. Gap Analysis")
    desired_profile = st.selectbox(
        "Profilo di Rischio Desiderato dal Cliente",
        profile_names_list,
        index=profile_names_list.index("3. Bilanciato")
    )
    
    submitted = st.form_submit_button("Genera Report di Profilazione")

if submitted:
    client_data, profilo_iniziale_calc = profiler._determine_profile(name, total_score, details)
    client_data.ProfiloDesiderato = desired_profile
    
    # Logica di Giustificazione immediata per l'output
    if client_data.ProfiloRischio != desired_profile:
        st.session_state.show_justification = True
        st.session_state.client_data_temp = client_data
        st.warning(f"⚠️ **DISALLINEAMENTO:** Profilo Calcolato è **{client_data.ProfiloRischio}** ma Desiderato è **{desired_profile}**.")
    else:
        client_data.Giustificazione = "Profilo calcolato e desiderato sono allineati."
        st.session_state.show_justification = False
        st.session_state.profile_results = client_data

# Se c'è un disallineamento, mostra il campo di giustificazione
if 'show_justification' in st.session_state and st.session_state.show_justification:
    client_data_temp = st.session_state.client_data_temp
    
    justification = st.text_area("Inserisci la Giustificazione del Disallineamento (richiesta MiFID):")
    
    if st.button("Conferma Giustificazione e Report Finale"):
        client_data_temp.Giustificazione = justification if justification else "Nessuna giustificazione fornita."
        st.session_state.profile_results = client_data_temp
        st.session_state.show_justification = False
        st.rerun() 


if st.session_state.profile_results and not st.session_state.get('show_justification', False):
    client = st.session_state.profile_results
    
    st.success("✅ Profilazione Completata!")
    st.subheader(f"Profilo Assegnato: **{client.ProfiloRischio.upper()}**")
    st.metric("Punteggio Totale", f"{client.PunteggioTotale} / {profiler.PUNTEGGIO_MAX}")
    st.info(f"Allocazione Suggerita: **{client.AllocazioneSuggerita}**")
    
    # 1. Visualizzazione Grafico
    fig = profiler.create_plot(client)
    st.pyplot(fig)
    
    st.markdown("---")
    st.subheader("Riepilogo e Conformità MiFID")
    st.json({
        "Cliente": client.NomeCliente,
        "Profilo Calcolato": client.ProfiloRischio,
        "Profilo Desiderato": client.ProfiloDesiderato,
        "Gap Coerenza": "DISALLINEATO" if client.ProfiloRischio != client.ProfiloDesiderato else "ALLINEATO",
        "Giustificazione": client.Giustificazione
    })
    
    # 2. Aggiornamento dello Storico e Generazione del Download
    
    df_new = client.to_dataframe()
    df_full = pd.concat([st.session_state.historical_df, df_new], ignore_index=True)
    
    excel_data = profiler.generate_excel_report(client, df_full)
    
    st.download_button(
        label="⬇️ Scarica Report Excel Completo (Storico + Grafico)",
        data=excel_data,
        file_name=f"Report_Rischio_{client.NomeCliente.replace(' ', '_')}_{client.DataOra[:10]}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )
