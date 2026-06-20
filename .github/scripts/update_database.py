import sys
import os
import requests

if __name__ == "__main__":
    # Preluăm argumentele trimise din formularul GitHub
    data_input = sys.argv[1]
    numere_raw = sys.argv[2]
    
    # Parsăm și ordonăm numerele, apoi calculăm suma
    numere = [int(n.strip()) for n in numere_raw.split(",")]
    numere.sort()
    suma = sum(numere)
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    # Payload-ul pentru tabela ta (ajustează numele tabelei și al coloanelor dacă e cazul)
    url = f"{supabase_url}/rest/v1/loto_history"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    data = {
        "data": data_input,
        "numere": numere, # Trimite array-ul sortat
        "suma": suma
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"✅ Succes! Adăugat: {data_input} -> {numere} (Suma: {suma})")
    else:
        print(f"❌ Eroare la insert: {response.text}")
        sys.exit(1)
