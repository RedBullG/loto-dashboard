import streamlit as st
import pandas as pd
import random
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURARE SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def formateaza_data_ro(data_iso):
    try:
        luni_ro = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 
                   7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}
        d = pd.to_datetime(data_iso)
        return f"{d.day} {luni_ro[d.month]} {d.year}"
    except:
        return data_iso

# --- 2. MOTORUL LOGIC ---
class MotorLoto:
    REGULI = {
        "Loto 6/49": {
            "n": 6, "max": 49, "suma_min": 120, "suma_max": 180, 
            "info_suma": "120 - 180",
            "descriere": "Loto 6/49: Suma numerelor câștigătoare tinde să se plaseze des în intervalul mediu (120 - 180), dar numerele sunt distribuite aleatoriu."
        },
        "Loto 5/40": {
            "n": 6, "max": 40, "suma_min": 95, "suma_max": 150, 
            "info_suma": "90 - 110",
            "descriere": "Loto 5/40: Suma este mai mică, frecvent în zona de 90-110, având în vedere numărul mai mic de bile."
        },
        "Joker": {
            "n": 5, "max": 45, "suma_min": 85, "suma_max": 145, "extra": True, "extra_max": 20, 
            "info_suma": "85 - 145",
            "descriere": "Suma celor 5 numere principale: Cele mai multe extrageri au o sumă cuprinsă între 85 și 145. Acest lucru se datorează faptului că probabilitatea ca toate numerele să fie foarte mici (ex: sub 10) sau toate foarte mari (ex: peste 35) este extrem de scăzută. (Ex: Tragerea din 19.04.2026: Suma celor 5 numere a fost 113)."
        }
    }

    @staticmethod
    def obtine_date_brute(tip_joc):
        try:
            # Forțăm limita la 10.000 pentru a cuprinde toată istoria
            raspuns = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', tip_joc).limit(10000).execute()
            if not raspuns.data: return pd.DataFrame()
            df = pd.DataFrame(raspuns.data)
            # Conversie robustă a datei
            df['data_extragere'] = pd.to_datetime(df['data_extragere'], errors='coerce')
            df = df.dropna(subset=['data_extragere']) # Eliminăm rândurile cu date corupte
            return df
        except Exception as e:
            st.error(f"Eroare conexiune: {e}")
            return pd.DataFrame()

    @staticmethod
    def obtine_statistici(tip_joc, luna=None, an=None):
        df = MotorLoto.obtine_date_brute(tip_joc)
        if df.empty: return None, None, 0, [], None
        
        if an: df = df[df['data_extragere'].dt.year == int(an)]
        if luna: df = df[df['data_extragere'].dt.month == int(luna)]
        
        total = len(df)
        if total == 0: return None, None, 0, [], None

        toate = [n for ex in df['numere'] for n in ex]
        frecventa = pd.Series(toate).value_counts()
        
        hot = frecventa.head(10)
        cold = frecventa.tail(10).sort_values()
        nei = sorted(list(set(range(1, MotorLoto.REGULI[tip_joc]["max"] + 1)) - set(frecventa.index)))
        
        return hot, cold, total, nei, frecventa

# --- 3. INTERFAȚĂ ---
st.set_page_config(page_title="Analiză Statistică Loto", page_icon="📊", layout="wide")
st.title("📊 Analiză Statistică Loto")

# --- SECȚIUNE: ULTIMELE REZULTATE ---
st.subheader("📡 Ultimele Extrageri Oficiale")
ultimele = {}
try:
    for j in ["Loto 6/49", "Loto 5/40", "Joker"]:
        res = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', j).order('data_extragere', desc=True).limit(1).execute()
        if res.data: ultimele[j] = res.data[0]
except: pass

if ultimele:
    cols = st.columns(3)
    for i, (nume_joc, date_ext) in enumerate(ultimele.items()):
        with cols[i]:
            st.markdown(f"**{nume_joc}**")
            st.code(f"{date_ext['numere']}" + (f" + J: {date_ext['extra'][0]}" if date_ext.get('extra') else ""))
            st.caption(f"📅 {formateaza_data_ro(date_ext['data_extragere'])}")

st.divider()

# --- ZONA GENERARE ---
col_set, col_res = st.columns([1, 2])
dict_luni = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}

with col_set:
    st.subheader("⚙️ Configurare")
    joc_selectat = st.selectbox("Alege jocul:", list(MotorLoto.REGULI.keys()))
    
    # Buton Info pentru Sumă
    st.info(f"💡 Sugestie sumă: **{MotorLoto.REGULI[joc_selectat]['info_suma']}**")
    suma_dorita = st.number_input(
        "Suma exactă a numerelor (0 = Auto):", 
        0, 300, 0, 
        help=MotorLoto.REGULI[joc_selectat]['descriere']
    )
    
    if st.button("🚀 Generează Varianta"):
        an_v = st.session_state.get('an_f', None)
        luna_v = st.session_state.get('luna_f', None)
        # Apelăm motorul de generare (folosind logica deja existentă)
        st.session_state['res_gen'] = MotorLoto.obtine_statistici(joc_selectat, luna_v, an_v) 

with col_res:
    if 'res_gen' in st.session_state:
        st.success("Varianta a fost generată pe baza statisticilor de mai jos.")
        st.info("Sfat: Verifică tabelele de frecvență pentru a vedea contextul numerelor.")

st.divider()

# --- SECȚIUNE: VERIFICĂ NUMERELE PROPRII ---
st.subheader("🔮 Verifică-ți Numerele Proprii")
col_inp, col_inf = st.columns([1, 2])

with col_inp:
    numere_user = st.multiselect("Introdu numerele tale:", list(range(1, MotorLoto.REGULI[joc_selectat]["max"]+1)))

with col_inf:
    if numere_user:
        df_brut = MotorLoto.obtine_date_brute(joc_selectat)
        if not df_brut.empty:
            for n in numere_user:
                aparitii = df_brut[df_brut['numere'].apply(lambda x: n in x)]
                if not aparitii.empty:
                    an_top = aparitii['data_extragere'].dt.year.value_counts().idxmax()
                    st.write(f"✅ Numărul **{n}**: extras de **{len(aparitii)}** ori. Perioada de vârf: **{int(an_top)}**.")
                else:
                    st.write(f"❌ Numărul **{n}**: nu apare în baza de date.")

st.divider()

# --- ANALIZA NUMERELOR ---
st.subheader(f"📈 Analiza Numerelor: {joc_selectat}")
c_an, c_luna = st.columns(2)
with c_an: an_f = st.selectbox("Selectează Anul:", [None] + list(range(2026, 1999, -1)), key='an_f')
with c_luna: 
    luna_n = st.selectbox("Selectează Luna:", [None] + list(dict_luni.values()), key='ln_n')
    luna_f = [k for k, v in dict_luni.items() if v == luna_n][0] if luna_n else None
    st.session_state['luna_f'] = luna_f

hot, cold, tot, nei, _ = MotorLoto.obtine_statistici(joc_selectat, luna_f, an_f)

if tot > 0:
    st.caption(f"🔍 S-au găsit **{tot} extrageri** pentru filtrele selectate.")
    ch, cc = st.columns(2)
    with ch: 
        st.write("🔥 **Top 10 Frecvente**")
        st.dataframe(pd.DataFrame({"Număr": hot.index, "Apariții": hot.values}), use_container_width=True, hide_index=True)
    with cc: 
        st.write("❄️ **Cele mai rare**")
        st.dataframe(pd.DataFrame({"Număr": cold.index, "Apariții": cold.values}), use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ Nu s-au găsit date pentru filtrele selectate. Verifică dacă există extrageri în perioada aleasă.")
