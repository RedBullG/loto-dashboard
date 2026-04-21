import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURARE SUPABASE (SECURIZAT PENTRU CLOUD) ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def formateaza_data_ro(data_iso):
    try:
        luni_ro = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 
                   7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}
        d = datetime.strptime(str(data_iso).split('T')[0], '%Y-%m-%d')
        return f"{d.day} {luni_ro[d.month]} {d.year}"
    except:
        return data_iso

# --- 2. MOTORUL LOGIC MULTI-JOC ---
class MotorLoto:
    REGULI = {
        "Loto 6/49": {
            "n": 6, "max": 49, "suma_min": 120, "suma_max": 180, "extra": False, 
            "info_suma": "120 - 180 (Media istorică)",
            "descriere": "Suma numerelor câștigătoare tinde să se plaseze des în intervalul mediu (120 - 180), dar numerele sunt distribuite aleatoriu."
        },
        "Loto 5/40": {
            "n": 6, "max": 40, "suma_min": 95, "suma_max": 150, "extra": False, 
            "info_suma": "90 - 110 (Frecvent pentru 5/40)",
            "descriere": "Suma este mai mică, frecvent în zona de 90-110, având în vedere numărul mai mic de bile."
        },
        "Joker": {
            "n": 5, "max": 45, "suma_min": 85, "suma_max": 145, "extra": True, "extra_max": 20, 
            "info_suma": "85 - 145 (Suma celor 5 numere)",
            "descriere": "Suma celor 5 numere principale: Cele mai multe extrageri au o sumă cuprinsă între 85 și 145. Acest lucru se datorează faptului că probabilitatea ca toate numerele să fie foarte mici (ex: sub 10) sau toate foarte mari (ex: peste 35) este extrem de scăzută."
        }
    }

    @staticmethod
    def obtine_date_brute(tip_joc):
        try:
            raspuns = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', tip_joc).execute()
            if not raspuns.data: return pd.DataFrame()
            df = pd.DataFrame(raspuns.data)
            df['data_extragere'] = pd.to_datetime(df['data_extragere'], errors='coerce')
            return df
        except:
            return pd.DataFrame()

    @staticmethod
    def obtine_statistici_avansate(tip_joc, luna=None, an=None):
        df = MotorLoto.obtine_date_brute(tip_joc)
        if df.empty: return None, None, 0, [], None
        
        if an: df = df[df['data_extragere'].dt.year == an]
        if luna: df = df[df['data_extragere'].dt.month == luna]
        
        total_extrageri = len(df)
        if total_extrageri == 0: return None, None, 0, [], None

        toate_numerele = [n for ex in df['numere'] for n in ex]
        frecventa = pd.Series(toate_numerele).value_counts()
        
        hot = frecventa.head(10)
        cold = frecventa.tail(10).sort_values()
        neiesite = sorted(list(set(range(1, MotorLoto.REGULI[tip_joc]["max"] + 1)) - set(frecventa.index)))
        
        return hot, cold, total_extrageri, neiesite, frecventa

    @staticmethod
    def genereaza_varianta(tip_joc, luna=None, an=None, suma_tinta=None):
        r = MotorLoto.REGULI[tip_joc]
        _, _, _, _, frecventa = MotorLoto.obtine_statistici_avansate(tip_joc, luna, an)
        numere_hot = frecventa.head(15).index.tolist() if frecventa is not None else []
        
        incercari = 0
        while incercari < 50000:
            incercari += 1
            if len(numere_hot) >= 3:
                baza = random.sample(numere_hot, 3)
                varianta = sorted(baza + random.sample([n for n in range(1, r["max"] + 1) if n not in baza], r["n"] - 3))
            else:
                varianta = sorted(random.sample(range(1, r["max"] + 1), r["n"]))
            
            suma = sum(varianta)
            if (suma == suma_tinta if suma_tinta else r["suma_min"] <= suma <= r["suma_max"]):
                pare = sum(1 for n in varianta if n % 2 == 0)
                if (r["n"] == 6 and pare in [2,3,4]) or (r["n"] == 5 and pare in [2,3]):
                    res = {"numere": varianta, "suma": suma, "extra": [random.randint(1, r["extra_max"])] if r.get("extra") else []}
                    return res
        return {"eroare": "Nu s-a găsit variantă. Încearcă altă sumă."}

# --- 3. INTERFAȚĂ ---
st.set_page_config(page_title="Analiză Statistică Loto", page_icon="🎲", layout="wide")
st.title("📊 Analiză Statistică Loto")

# --- ULTIMELE REZULTATE ---
st.subheader("📡 Ultimele Extrageri Oficiale")
ultimele = {}
try:
    for j in ["Loto 6/49", "Loto 5/40", "Joker"]:
        res = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', j).order('data_extragere', desc=True).limit(1).execute()
        if res.data: ultimele[j] = res.data[0]
except: pass

if ultimele:
    cols = st.columns(3)
    for i, j in enumerate(["Loto 6/49", "Loto 5/40", "Joker"]):
        with cols[i]:
            if j in ultimele:
                date_ext = ultimele[j]
                st.markdown(f"**{j}**")
                st.code(f"{date_ext['numere']}" + (f" + Joker: {date_ext['extra'][0]}" if date_ext.get('extra') else ""))
                st.caption(f"📅 Data: {formateaza_data_ro(date_ext['data_extragere'])}")
            else:
                st.markdown(f"**{j}**\nNicio dată disponibilă.")
else:
    st.info("Baza de date este goală sau se încarcă.")

st.divider()

# --- ZONA GENERARE & FILTRE ---
col_set, col_res = st.columns([1, 2])
dict_luni = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}

with col_set:
    st.subheader("⚙️ Configurare")
    joc_selectat = st.selectbox("Joc:", list(MotorLoto.REGULI.keys()))
    
    st.info(f"💡 Suma optimă {joc_selectat}: **{MotorLoto.REGULI[joc_selectat]['info_suma']}**")
    
    # Aici este tooltip-ul pentru informații suplimentare
    suma_dorita = st.number_input(
        "Suma exactă (Lasă 0 pt. Auto):", 
        min_value=0, 
        max_value=300, 
        value=0, 
        step=1,
        help=MotorLoto.REGULI[joc_selectat]['descriere']
    )
    
    if st.button("🚀 Generează"):
        an_v = st.session_state.get('an_f', None)
        luna_v = st.session_state.get('luna_f', None)
        st.session_state['res_gen'] = MotorLoto.genereaza_varianta(joc_selectat, luna_v, an_v, suma_dorita if suma_dorita > 0 else None)

with col_res:
    if 'res_gen' in st.session_state:
        rg = st.session_state['res_gen']
        if "eroare" in rg: st.error(rg["eroare"])
        else:
            st.success(f"### Varianta: `{rg['numere']}` " + (f" + Joker: `{rg['extra']}`" if rg['extra'] else ""))
            st.markdown(f"**Suma:** `{rg['suma']}`")

st.divider()

# --- SECȚIUNE NOUĂ: VERIFICĂ NUMERELE TALE ---
st.subheader("🔮 Verifică-ți Numerele Proprii")
col_inp, col_inf = st.columns([1, 2])

with col_inp:
    numere_user = st.multiselect("Alege numerele jucate:", list(range(1, MotorLoto.REGULI[joc_selectat]["max"]+1)))

with col_inf:
    if numere_user:
        df_brut = MotorLoto.obtine_date_brute(joc_selectat)
        if not df_brut.empty:
            for n in numere_user:
                aparitii = df_brut[df_brut['numere'].apply(lambda x: n in x)]
                if not aparitii.empty:
                    an_top = aparitii['data_extragere'].dt.year.value_counts().idxmax()
                    st.write(f"✅ Numărul **{n}**: extras de **{len(aparitii)}** ori. Cea mai activă perioadă: **{an_top}**.")
                else:
                    st.write(f"❌ Numărul **{n}**: nu a fost extras în baza de date selectată.")

st.divider()

# --- STATISTICI ---
st.subheader(f"📊 Top Numere: {joc_selectat}")
c_an, c_luna = st.columns(2)
with c_an: an_f = st.selectbox("An:", [None] + list(range(2026, 2020, -1)), key='an_f')
with c_luna: 
    luna_n = st.selectbox("Lună:", [None] + list(dict_luni.values()), key='ln_n')
    luna_f = [k for k, v in dict_luni.items() if v == luna_n][0] if luna_n else None
    st.session_state['luna_f'] = luna_f

hot, cold, tot, nei, _ = MotorLoto.obtine_statistici_avansate(joc_selectat, luna_f, an_f)

if tot > 0:
    ch, cc = st.columns(2)
    with ch: st.table(pd.DataFrame({"Număr": hot.index, "Frecvență": hot.values}))
    with cc: st.table(pd.DataFrame({"Număr": cold.index, "Frecvență": cold.values}))
else:
    st.warning("Nu există date pentru filtrele selectate.")
