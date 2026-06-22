import sys
import os
import requests
import json

if __name__ == "__main__":
    # Preluăm doar cele 3 argumente din formular
    tip_joc_input = sys.argv[1]   # '6/49', '5/40' sau 'Joker'
    data_input = sys.argv[2]       # Data (YYYY-MM-DD)
    numere_raw = sys.argv[3]       # Numerele introduse ca text
    
    # Citim din env și curățăm la sânge orice Enter (\n) sau spațiu rătăcit
    raw_url = os.environ.get("SUPABASE_URL", "")
    raw_key = os.environ.get("SUPABASE_KEY", "")
    
    supabase_url = raw_url.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    supabase_key = raw_key.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    
    if not supabase_url or not supabase_key:
        print("❌ Eroare: URL-ul sau KEY-ul pentru Supabase sunt goale în setările GitHub!")
        sys.exit(1)
        
    url = f"{supabase_url}/rest/v1/rezultate_oficiale"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    # Formatăm tipul de joc exact cum apare în tabela ta
    tip_joc_map = {
        "6/49": "Loto 6/49",
        "5/40": "Loto 5/40",
        "Joker": "Joker"
    }
    tip_joc_final = tip_joc_map.get(tip_joc_input)

    # Inițializăm structura de date pentru Supabase
    numere_principale = []
    numere_extra = []

    # Procesăm numerele în funcție de joc
    if tip_joc_input == "Joker":
        if "+" not in numere_raw:
            print("❌ Pentru Joker adaugă bila extra cu '+'. Exemplu: 3,17,28,38,40 + 11")
            sys.exit(1)
        principale_part, extra_part = numere_raw.split("+")
        numere_principale = [int(n.strip()) for n in principale_part.split(",") if n.strip()]
        numere_principale.sort()
        numere_extra = [int(extra_part.strip())]
    else:
        numere_principale = [int(n.strip()) for n in numere_raw.split(",") if n.strip()]
        numere_principale.sort()
        numere_extra = []

    payload = {
        "tip_joc": tip_joc_final,
        "data_extragere": data_input,
        "numere": numere_principale,
        "extra": numere_extra
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"✅ [{tip_joc_final}] Inserat cu succes: {data_input} -> {numere_principale}")
    else:
        print(f"❌ Eroare HTTP {response.status_code}: {response.text}")
        sys.exit(1)
