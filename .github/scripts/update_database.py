import sys
import requests
import json

if __name__ == "__main__":
    # Preluăm toate cele 5 argumente transmise direct din linia de comandă GitHub
    tip_joc_input = sys.argv[1]   # '6/49', '5/40' sau 'Joker'
    data_input = sys.argv[2]       # Data (YYYY-MM-DD)
    numere_raw = sys.argv[3]       # Numerele introduse ca text
    
    # Adăugăm .strip() direct pe argumente ca să ștergem instant orice Enter (\n) ascuns din GitHub Secrets
    supabase_url = sys.argv[4].strip().replace("\n", "").replace("\r", "")
    supabase_key = sys.argv[5].strip().replace("\n", "").replace("\r", "")
    
    if not supabase_url or not supabase_key:
        print("❌ Eroare: URL-ul sau KEY-ul pentru Supabase nu au fost găsite în argumente!")
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
        # Format așteptat la input de pe telefon: 3,17,28,38,40 + 11
        if "+" not in numere_raw:
            print("❌ Pentru Joker adaugă bila extra cu '+'. Exemplu: 3,17,28,38,40 + 11")
            sys.exit(1)
            
        principale_part, extra_part = numere_raw.split("+")
        
        numere_principale = [int(n.strip()) for n in principale_part.split(",") if n.strip()]
        numere_principale.sort()
        
        # Bila de Joker se salvează tot ca un array cu un singur element [X] conform tabelei tale
        numere_extra = [int(extra_part.strip())]
    else:
        # Pentru 6/49 și 5/40: 2,12,15,20,27,36
        numere_principale = [int(n.strip()) for n in numere_raw.split(",") if n.strip()]
        numere_principale.sort()
        numere_extra = [] # Rămâne array gol [] exact ca în screenshot

    # Payload-ul exact pentru structura bazei tale de date
    payload = {
        "tip_joc": tip_joc_final,
        "data_extragere": data_input,
        "numere": numere_principale,  # Trimis ca array de întregi
        "extra": numere_extra          # Trimis ca array de întregi ([] sau [X])
    }
    
    # Trimitere request către REST API Supabase
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"✅ [{tip_joc_final}] Inserat cu succes: {data_input} -> {numere_principale} | Extra: {numere_extra}")
    else:
        print(f"❌ Eroare HTTP {response.status_code}: {response.text}")
        sys.exit(1)
