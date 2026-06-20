import sys
import os
import requests

if __name__ == "__main__":
    # Preluăm cele 3 argumente transmise de GitHub
    tip_joc = sys.argv[1]       # '6/49', '5/40' sau 'Joker'
    data_input = sys.argv[2]     # Data
    numere_raw = sys.argv[3]     # Numerele ca text
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    # --- LOGICA ÎN FUNCȚIE DE TIPUL DE JOC ---
    
    if tip_joc == "6/49":
        numere = [int(n.strip()) for n in numere_raw.split(",")]
        numere.sort()
        payload = {
            "data": data_input,
            "numere": numere,
            "suma": sum(numere)
        }
        url = f"{supabase_url}/rest/v1/loto_649" # Numele tabelei tale pentru 6/49

    elif tip_joc == "5/40":
        numere = [int(n.strip()) for n in numere_raw.split(",")]
        numere.sort()
        payload = {
            "data": data_input,
            "numere": numere,
            "suma": sum(numere)
        }
        url = f"{supabase_url}/rest/v1/loto_540" # Numele tabelei tale pentru 5/40

    elif tip_joc == "Joker":
        # Pentru Joker, poți introduce numerele în formatul: 5,12,19,23,40 + 14
        # Împărțim textul în zona numerelor principale și a Joker-ului
        try:
            principale_raw, joker_raw = numere_raw.split("+")
            numere_principale = [int(n.strip()) for n in principale_raw.split(",")]
            numere_principale.sort()
            numar_joker = int(joker_raw.strip())
        except ValueError:
            print("❌ Format greșit pentru Joker! Folosește: 1,2,3,4,5 + 20")
            sys.exit(1)
            
        payload = {
            "data": data_input,
            "numere_principale": numere_principale,
            "joker": numar_joker,
            "suma_principale": sum(numere_principale)
        }
        url = f"{supabase_url}/rest/v1/loto_joker" # Numele tabelei tale pentru Joker

    # --- TRIMITEREA CĂTRE SUPABASE ---
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"✅ [{tip_joc}] Update realizat cu succes pentru data {data_input}!")
    else:
        print(f"❌ Eroare la salvarea în Supabase: {response.text}")
        sys.exit(1)
