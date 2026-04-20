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
    """Transformă YYYY-MM-DD în format românesc elegant"""
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
        "Loto 6/49": {"n": 6, "max": 49, "suma_min": 120, "suma_max": 180, "extra": False},
        "Loto 5/40": {"n": 6, "max": 40, "suma_min": 95, "suma_max": 150, "extra": False},
        "Joker": {"n": 5, "max": 45, "suma_min": 115, "suma_max": 130, "extra": True, "extra_max": 20}
    }

    @staticmethod
    def obtine_ultimele_rezultate():
        jocuri = ["Loto 6/49", "Loto 5/40", "Joker"]
        rezultate = {}
        azi_iso = datetime.now().strftime('%Y-%m-%d')
        
        try:
            for joc in jocuri:
                raspuns = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', joc).lte('data_extragere', azi_iso).order('data_extragere', desc=True).limit(1).execute()
                if raspuns.data:
                    rezultate[joc] = raspuns.data[0]
        except:
            pass
        return rezultate

    @staticmethod
    def obtine_statistici_avansate(tip_joc, luna=None, an=None):
        try:
            raspuns = supabase.table('rezultate_oficiale').select('numere, data_extragere').eq('tip_joc', tip_joc).execute()
            if not raspuns.data:
                return None, None, 0, [], None
            
            df = pd.DataFrame(raspuns.data)
            df['data_extragere'] = pd.to_datetime(df['data_extragere'])
            
            if an: df = df[df['data_extragere'].dt.year == an]
            if luna: df = df[df['data_extragere'].dt.month == luna]
            
            total_extrageri = len(df)
            if total_extrageri == 0:
                return None, None, 0, [], None

            toate_numerele = [n for ex in df['numere'] for n in ex]
            frecventa = pd.Series(toate_numerele).value_counts()
            
            hot = frecventa.head(10)
            cold = frecventa.tail(10).sort_values()
            
            toate_posibile = set(range(1, MotorLoto.REGULI[tip_joc]["max"] + 1))
            iesite = set(frecventa.index)
            neiesite = sorted(list(toate_posibile - iesite))
            
            return hot, cold, total_extrageri, neiesite, frecventa
        except:
            return None, None, 0, [], None

    @staticmethod
    def genereaza_varianta(tip_joc, luna=None, an=None, suma_tinta=None):
        r = MotorLoto.REGULI[tip_joc]
        _, _, _, _, frecventa = MotorLoto.obtine_statistici_avansate(tip_joc, luna, an)
        
        numere_hot = frecventa.head(15).index.tolist() if frecventa is not None else []
        
        valid = False
        incercari = 0
        max_incercari = 50000 
        
        while not valid:
            incercari += 1
            if incercari > max_incercari:
                return {"eroare": f"Nu s-a putut găsi o variantă validă care să însumeze exact {suma_tinta}. Încearcă altă sumă!"}

            if len(numere_hot) >= 3:
                baza = random.sample(numere_hot, 3)
                posibile = [n for n in range(1, r["max"] + 1) if n not in baza]
                restul = random.sample(posibile, r["n"] - 3)
                varianta = sorted(baza + restul)
            else:
                varianta = sorted(random.sample(range(1, r["max"] + 1), r["n"]))
            
            suma = sum(varianta)
            suma_ok = (suma == suma_tinta) if suma_tinta else (r["suma_min"] <= suma <= r["suma_max"])
            
            if suma_ok:
                pare = sum(1 for n in varianta if n % 2 == 0)
                if (r["n"] == 6 and pare in [2, 3, 4]) or (r["n"] == 5 and pare in [2, 3]):
                    rezultat = {
                        "numere": varianta, 
                        "suma": suma, 
                        "incercari": incercari,
                        "hot_used": len(set(varianta) & set(numere_hot))
                    }
                    rezultat["extra"] = [random.randint(1, r["extra_max"])] if r["extra"] else []
                    return rezultat

    @staticmethod
    def analiza_performanta_istorica(numere_gen, extra_gen, tip_joc, luna=None, an=None):
        try:
            raspuns = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', tip_joc).execute()
            if not raspuns.data:
                return None
            
            df = pd.DataFrame(raspuns.data)
            df['data_extragere'] = pd.to_datetime(df['data_extragere'])
            
            if an: df = df[df['data_extragere'].dt.year == an]
            if luna: df = df[df['data_extragere'].dt.month == luna]
            
            arhiva = df.to_dict('records')
            stats = {"Cat_I": 0, "Cat_II": 0, "Cat_III": 0, "Cat_IV": 0, "total": len(arhiva)}
            
            for ex in arhiva:
                potriviri = len(set(numere_gen) & set(ex['numere']))
                
                if tip_joc == "Loto 6/49":
                    if potriviri == 6: stats["Cat_I"] += 1
                    elif potriviri == 5: stats["Cat_II"] += 1
                    elif potriviri == 4: stats["Cat_III"] += 1
                    elif potriviri == 3: stats["Cat_IV"] += 1
                elif tip_joc == "Loto 5/40":
                    if potriviri >= 5: stats["Cat_I"] += 1
                    elif potriviri == 4: stats["Cat_II"] += 1
                elif tip_joc == "Joker":
                    extra_match = extra_gen[0] == ex['extra'][0] if extra_gen and ex['extra'] else False
                    if potriviri == 5 and extra_match: stats["Cat_I"] += 1
                    elif potriviri == 5: stats["Cat_II"] += 1
                    elif potriviri == 4 and extra_match: stats["Cat_III"] += 1
                    elif potriviri == 4: stats["Cat_IV"] += 1
            return stats
        except:
            return None

# --- 3. INTERFAȚA GRAFICĂ (FRONTEND) ---
st.set_page_config(page_title="Analiză Loto Pro", page_icon="🎲", layout="wide")

st.title("🎲 Centru de Comandă Loto")

# --- PANOU SUPERIOR: ULTIMELE REZULTATE ---
st.subheader("📡 Ultimele Extrageri Oficiale")
ultimele_rezultate = MotorLoto.obtine_ultimele_rezultate()

if ultimele_rezultate:
    cols = st.columns(3)
    for i, joc in enumerate(["Loto 6/49", "Loto 5/40", "Joker"]):
        with cols[i]:
            if joc in ultimele_rezultate:
                date = ultimele_rezultate[joc]
                st.markdown(f"**{joc}**")
                st.code(f"{date['numere']}" + (f" + Joker: {date['extra'][0]}" if date.get('extra') else ""))
                st.caption(f"📅 Data: {formateaza_data_ro(date['data_extragere'])}")
            else:
                st.markdown(f"**{joc}**\nNicio dată disponibilă.")
else:
    st.info("Baza de date este goală sau se încarcă.")

st.write("---")

# --- ZONA DE SETĂRI ȘI GENERARE ---
# Folosim containere pentru a separa vizual secțiunile
col_setari, col_rezultat = st.columns([1, 2])

# Declarăm aici variabilele de timp pentru a fi accesibile butonului de generare de mai sus
# Deși sunt vizual mai jos, Streamlit le va procesa corect
dict_luni = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 
             7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}

with col_setari:
    st.subheader("⚙️ Setări Generare")
    joc_selectat = st.selectbox("Alege tipul de joc:", ["Loto 6/49", "Loto 5/40", "Joker"])
    
    suma_dorita = st.number_input("Suma exactă (Lasă 0 pt. Auto):", min_value=0, max_value=300, value=0, step=1)
    suma_tinta = suma_dorita if suma_dorita > 0 else None

    # Butonul de generare - va folosi filtrele de timp definite în secțiunea de analiză de mai jos
    if st.button(f"🚀 Generează Varianta", use_container_width=True):
        with st.spinner('Căutăm combinația perfectă...'):
            # Notă: an_selectat și luna_selectata sunt declarate mai jos, dar disponibile prin rerun-ul Streamlit
            an_val = st.session_state.get('an_filtre', None)
            luna_val = st.session_state.get('luna_filtre', None)
            
            rezultat = MotorLoto.genereaza_varianta(joc_selectat, luna_val, an_val, suma_tinta)
            
            if "eroare" in rezultat:
                st.error(rezultat["eroare"])
            else:
                verificare = MotorLoto.analiza_performanta_istorica(rezultat["numere"], rezultat["extra"], joc_selectat, luna_val, an_val)
                st.session_state['ultima_verificare'] = verificare
                st.session_state['ultimul_rezultat'] = rezultat

with col_rezultat:
    st.subheader("🎯 Rezultatul Tău")
    if 'ultimul_rezultat' in st.session_state:
        res = st.session_state['ultimul_rezultat']
        verif = st.session_state['ultima_verificare']
        
        st.success(f"### Varianta Generată: `{res['numere']}` " + (f" + Joker: `{res['extra']}`" if res['extra'] else ""))
        st.markdown(f"**Suma Totală a Numerelor:** `{res['suma']}`")
        
        if verif:
            st.caption(f"🔍 Performanță verificată pe {verif['total']} extrageri conform filtrelor de mai jos.")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Cat. I", verif["Cat_I"])
            c2.metric("Cat. II", verif["Cat_II"])
            c3.metric("Cat. III", verif["Cat_III"])
            c4.metric("Cat. IV", verif["Cat_IV"])
    else:
        st.info("👈 Configurează setările și apasă butonul pentru a genera o variantă.")

st.write("---")

# --- PANOU DE ANALIZĂ ȘI STATISTICI ---
st.subheader(f"📊 Analiza Numerelor: {joc_selectat}")

# Mutăm aici filtrele de An și Lună, deasupra tabelului
col_an, col_luna = st.columns(2)
with col_an:
    an_selectat = st.selectbox("Filtrează după An:", [None] + list(range(2026, 1999, -1)), 
                               format_func=lambda x: "Toată Istoria" if x is None else str(x), key='an_filtre')
with col_luna:
    luna_nume = st.selectbox("Filtrează după Lună:", [None] + list(dict_luni.values()), 
                             format_func=lambda x: "Tot Anul" if x is None else x, key='luna_filtre_nume')
    luna_selectata = [k for k, v in dict_luni.items() if v == luna_nume][0] if luna_nume else None
    # Salvăm în session_state pentru a fi accesibil motorului de generare de sus
    st.session_state['luna_filtre'] = luna_selectata

hot, cold, total, neiesite, _ = MotorLoto.obtine_statistici_avansate(joc_selectat, luna_selectata, an_selectat)

if total > 0:
    st.caption(f"S-au analizat **{total} de extrageri** pentru perioada selectată.")
    
    col_h, col_c = st.columns(2)
    with col_h:
        st.write("🔥 **Top 10 Cel Mai Des Extrase**")
        df_hot = pd.DataFrame({"Număr": hot.index, "Apariții": hot.values})
        st.dataframe(df_hot, use_container_width=True, hide_index=True)
        
    with col_c:
        st.write("❄️ **Top 10 Cel Mai Rar Extrase**")
        df_cold = pd.DataFrame({"Număr": cold.index, "Apariții": cold.values})
        st.dataframe(df_cold, use_container_width=True, hide_index=True)
        
    if neiesite:
        st.warning(f"⚠️ **Numere care NU s-au extras deloc în această perioadă:** {', '.join(map(str, neiesite))}")
else:
    st.info("Nicio extragere găsită pentru filtrele selectate.")

st.write("---")

# --- TOP CÂȘTIGURI ISTORICE ---
st.subheader("🏆 Cele mai mari câștiguri din istoria Loteriei Române")
c_win1, c_win2, c_win3 = st.columns(3)
with c_win1:
    st.info("**Joker**\n\n65.969.447 lei\n\n19 Apr 2026")
with c_win2:
    st.success("**Loto 6/49**\n\n50.096.011 lei\n\n25 Iun 2023")
with c_win3:
    st.warning("**Loto 5/40**\n\n1.490.953 lei\n\n13 Ian 2019")
