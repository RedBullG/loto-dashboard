import streamlit as st
import pandas as pd
import random
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURARE SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def parse_data_smart(data_str):
    """Cititor universal de date (rezolvă conflictele între formatul ISO și cel European)"""
    try:
        d_str = str(data_str).split('T')[0]
        if '.' in d_str:
            return pd.to_datetime(d_str, format='%d.%m.%Y', errors='coerce')
        elif '/' in d_str:
            return pd.to_datetime(d_str, format='%d/%m/%Y', errors='coerce')
        else:
            return pd.to_datetime(d_str, format='%Y-%m-%d', errors='coerce')
    except:
        return pd.NaT

def formateaza_data_ro(data_iso):
    try:
        luni_ro = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 
                   7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}
        d = parse_data_smart(data_iso)
        if pd.notna(d):
            return f"{d.day} {luni_ro[d.month]} {d.year}"
        return data_iso
    except:
        return data_iso

# --- 2. MOTORUL LOGIC ---
class MotorLoto:
    REGULI = {
        "Loto 6/49": {
            "n": 6, "max": 49, "suma_min": 120, "suma_max": 180, "extra": False, 
            "info_suma": "120 - 180",
            "descriere": "Suma numerelor câștigătoare tinde să se plaseze des în intervalul mediu (120 - 180), dar numerele sunt distribuite aleatoriu."
        },
        "Loto 5/40": {
            "n": 6, "max": 40, "suma_min": 95, "suma_max": 150, "extra": False, 
            "info_suma": "90 - 110",
            "descriere": "Suma este mai mică, frecvent în zona de 90-110, având în vedere numărul mai mic de bile."
        },
        "Joker": {
            "n": 5, "max": 45, "suma_min": 85, "suma_max": 145, "extra": True, "extra_max": 20, 
            "info_suma": "85 - 145",
            "descriere": "Suma celor 5 numere principale: Cele mai multe extrageri au o sumă cuprinsă între 85 și 145. Acest lucru se datorează faptului că probabilitatea ca toate numerele să fie foarte mici sau toate foarte mari este extrem de scăzută."
        }
    }

    @staticmethod
    def obtine_date_brute(tip_joc):
        try:
            all_data = []
            start = 0
            step = 1000
            while True:
                raspuns = supabase.table('rezultate_oficiale').select('*').eq('tip_joc', tip_joc).order('data_extragere', desc=True).range(start, start + step - 1).execute()
                if not raspuns.data: break
                all_data.extend(raspuns.data)
                if len(raspuns.data) < step: break
                start += step
            if not all_data: return pd.DataFrame()
            df = pd.DataFrame(all_data)
            df['data_extragere_dt'] = df['data_extragere'].apply(parse_data_smart)
            df = df.dropna(subset=['data_extragere_dt'])
            df['data_extragere'] = df['data_extragere_dt']
            return df
        except Exception as e:
            st.error(f"Eroare preluare date din cloud: {e}")
            return pd.DataFrame()

    @staticmethod
    def obtine_statistici_avansate(tip_joc, luna=None, an=None):
        df = MotorLoto.obtine_date_brute(tip_joc)
        if df.empty: return None, None, 0, [], None
        if an: df = df[df['data_extragere'].dt.year == int(an)]
        if luna: df = df[df['data_extragere'].dt.month == int(luna)]
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
                posibile = [n for n in range(1, r["max"] + 1) if n not in baza]
                restul = random.sample(posibile, r["n"] - 3)
                varianta = sorted(baza + restul)
            else:
                varianta = sorted(random.sample(range(1, r["max"] + 1), r["n"]))
            suma = sum(varianta)
            if (suma == suma_tinta if suma_tinta else r["suma_min"] <= suma <= r["suma_max"]):
                pare = sum(1 for n in varianta if n % 2 == 0)
                if (r["n"] == 6 and pare in [2,3,4]) or (r["n"] == 5 and pare in [2,3]):
                    res = {"numere": varianta, "suma": suma, "extra": [random.randint(1, r["extra_max"])] if r.get("extra") else []}
                    return res
        return {"eroare": "Nu s-a găsit o variantă validă la suma respectivă."}

    @staticmethod
    def analiza_performanta_istorica(numere_gen, extra_gen, tip_joc, luna=None, an=None):
        df = MotorLoto.obtine_date_brute(tip_joc)
        if df.empty: return None
        if an: df = df[df['data_extragere'].dt.year == int(an)]
        if luna: df = df[df['data_extragere'].dt.month == int(luna)]
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

# --- 3. INTERFAȚĂ FRONTEND ---
st.set_page_config(page_title="Analiză Statistică Loto", page_icon="📊", layout="wide")
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
    for i, (nume_joc, date_ext) in enumerate(ultimele.items()):
        with cols[i]:
            st.markdown(f"**{nume_joc}**")
            st.code(f"{date_ext['numere']}" + (f" + J: {date_ext['extra'][0]}" if date_ext.get('extra') else ""))
            st.caption(f"📅 {formateaza_data_ro(date_ext['data_extragere'])}")
else:
    st.info("Baza de date se încarcă sau este goală.")

st.divider()

# --- ZONA GENERARE & FILTRE ---
col_set, col_res = st.columns([1, 2])
dict_luni = {1:"Ianuarie", 2:"Februarie", 3:"Martie", 4:"Aprilie", 5:"Mai", 6:"Iunie", 7:"Iulie", 8:"August", 9:"Septembrie", 10:"Octombrie", 11:"Noiembrie", 12:"Decembrie"}

with col_set:
    st.subheader("⚙️ Configurare")
    joc_selectat = st.selectbox("Alege jocul:", list(MotorLoto.REGULI.keys()))
    st.info(f"💡 Sugestie sumă: **{MotorLoto.REGULI[joc_selectat]['info_suma']}**")
    suma_dorita = st.number_input("Suma exactă (0 = Auto):", 0, 300, 0, help=MotorLoto.REGULI[joc_selectat]['descriere'])
    if st.button("🚀 Generează Varianta", use_container_width=True):
        with st.spinner("Căutăm combinația perfectă..."):
            an_v, luna_v = st.session_state.get('an_f'), st.session_state.get('luna_f')
            rezultat = MotorLoto.genereaza_varianta(joc_selectat, luna_v, an_v, suma_dorita if suma_dorita > 0 else None)
            st.session_state['res_gen'] = rezultat
            if "eroare" not in rezultat:
                st.session_state['verif_gen'] = MotorLoto.analiza_performanta_istorica(rezultat["numere"], rezultat["extra"], joc_selectat, luna_v, an_v)

with col_res:
    st.subheader("🎯 Rezultatul Tău")
    if 'res_gen' in st.session_state:
        rg = st.session_state['res_gen']
        if "eroare" in rg: st.error(rg["eroare"])
        else:
            st.success(f"### Varianta: `{rg['numere']}` " + (f" + J: `{rg['extra']}`" if rg['extra'] else ""))
            st.markdown(f"**Suma numerelor:** `{rg['suma']}`")
            verif = st.session_state.get('verif_gen')
            if verif:
                st.caption(f"🔍 Performanță verificată pe un total de {verif['total']} extrageri.")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Cat. I", verif["Cat_I"])
                c2.metric("Cat. II", verif["Cat_II"])
                c3.metric("Cat. III", verif["Cat_III"])
                c4.metric("Cat. IV", verif["Cat_IV"])
    else:
        st.info("👈 Setează preferințele și apasă butonul.")

st.divider()

# --- SECȚIUNE: VERIFICĂ NUMERELE PROPRII ---
st.subheader("🔮 Verifică-ți Numerele Proprii")
col_inp, col_inf = st.columns([1, 2])
with col_inp:
    n_cerute = MotorLoto.REGULI[joc_selectat]["n"]
    st.markdown(f"**Biletul tău ({joc_selectat})**")
    numere_user = st.multiselect(f"Alege {n_cerute} numere:", list(range(1, MotorLoto.REGULI[joc_selectat]["max"]+1)), max_selections=n_cerute)
    extra_user = []
    if MotorLoto.REGULI[joc_selectat].get("extra"):
        extra_val = st.selectbox("Alege Joker-ul:", [None] + list(range(1, MotorLoto.REGULI[joc_selectat]["extra_max"]+1)))
        if extra_val: extra_user = [extra_val]

with col_inf:
    if numere_user:
        df_brut = MotorLoto.obtine_date_brute(joc_selectat)
        st.markdown("**📊 Performanța Individuală:**")
        if not df_brut.empty:
            for n in numere_user:
                aparitii = df_brut[df_brut['numere'].apply(lambda x: n in x)]
                if not aparitii.empty:
                    an_top = aparitii['data_extragere'].dt.year.value_counts().idxmax()
                    st.write(f"🔹 **{n}**: extras de **{len(aparitii)}** ori. Anul de vârf: **{int(an_top)}**.")
        if len(numere_user) == n_cerute:
            st.markdown("---")
            st.markdown("**🏆 Istoric de Câștig al Variantei:**")
            verif_user = MotorLoto.analiza_performanta_istorica(numere_user, extra_user, joc_selectat)
            if verif_user:
                st.caption(f"Verificat pe {verif_user['total']} extrageri istorice.")
                cu1, cu2, cu3, cu4 = st.columns(4)
                cu1.metric("Cat. I", verif_user["Cat_I"]); cu2.metric("Cat. II", verif_user["Cat_II"])
                cu3.metric("Cat. III", verif_user["Cat_III"]); cu4.metric("Cat. IV", verif_user["Cat_IV"])
                tot_c = sum([verif_user[k] for k in ["Cat_I", "Cat_II", "Cat_III", "Cat_IV"]])
                if tot_c > 0: st.success(f"Bilet câștigător de **{tot_c}** ori!")
                else: st.warning("Biletul nu a câștigat nicio categorie până acum.")
    else:
        st.info(f"💡 Selectează exact {n_cerute} numere pentru backtesting complet.")

st.divider()

# --- ANALIZA NUMERELOR ---
st.subheader(f"📈 Analiza Numerelor: {joc_selectat}")
c_an, c_luna = st.columns(2)
with c_an: an_f = st.selectbox("An:", [None] + list(range(2026, 1992, -1)), format_func=lambda x: "Toată Istoria" if x is None else str(x), key='an_f')
with c_luna: 
    luna_n = st.selectbox("Lună:", [None] + list(dict_luni.values()), format_func=lambda x: "Tot Anul" if x is None else x, key='ln_n')
    luna_f = [k for k, v in dict_luni.items() if v == luna_n][0] if luna_n else None
    st.session_state['luna_f'] = luna_f
hot, cold, tot, nei, _ = MotorLoto.obtine_statistici_avansate(joc_selectat, luna_f, an_f)
if tot > 0:
    st.caption(f"🔍 Analizate **{tot} de extrageri**.")
    ch, cc = st.columns(2)
    with ch: st.dataframe(pd.DataFrame({"Număr": hot.index, "Apariții": hot.values}), use_container_width=True, hide_index=True)
    with cc: st.dataframe(pd.DataFrame({"Număr": cold.index, "Apariții": cold.values}), use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ Nu există date.")
