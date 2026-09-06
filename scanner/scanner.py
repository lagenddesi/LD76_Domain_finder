import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup

# --- KEYWORD MATRIX ---
PAYMENT_KEYWORDS = [
    "easypaisa", "easy paisa", "jazzcash", "jazz cash", "nayapay", "sadapay", 
    "raast", "mobicash", "meezan", "hbl", "ubl", "alfalah", "pkr", "rs."
]

PROFIT_KEYWORDS = [
    "daily profit", "daily income", "daily earning", "daily return", "roi",
    "vip 1", "vip level", "investment plan", "deposit plan", "rozana", "munafa"
]

ACTION_KEYWORDS = [
    "recharge", "deposit", "withdraw", "min deposit", "referral commission", "team commission"
]

PLATFORM_KEYWORDS = [
    "chat.whatsapp.com", "wa.me/", "t.me/"
]

def get_recent_domains(tld="top"):
    """crt.sh se pichle naye domains fetch karta hai"""
    print(f"[*] Fetching new .{tld} domains...")
    url = f"https://crt.sh/?q=%.{tld}&output=json"
    domains = set()
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            data = res.json()
            # Top 100 recent unique domains pick karein
            for item in data[-100:]:
                name = item.get('name_value', '').lower()
                # Wildcards ya multi-lines ko saaf karein
                for d in name.split('\n'):
                    d = d.replace('*.', '').strip()
                    if d.endswith(f".{tld}"):
                        domains.add(d)
    except Exception as e:
        print(f"[!] Error fetching crt.sh: {e}")
    return list(domains)

def analyze_site(domain):
    """Website visit kar ke score calculate karta hai"""
    url = f"https://{domain}"
    try:
        res = requests.get(url, timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code != 200:
            return None
    except:
        return None  # Inactive site drop

    soup = BeautifulSoup(res.text, 'html.parser')
    # Script aur styles delete karein
    for tag in soup(["script", "style"]):
        tag.decompose()
    
    text = soup.get_text().lower()
    html_raw = res.text.lower()

    # --- SCOREBOARD CALCULATION ---
    score = 0
    detected_payments = []
    
    for kw in PAYMENT_KEYWORDS:
        if kw in text:
            score += 40
            detected_payments.append(kw)
            break  # Ek baar payment group match ho gaya

    for kw in PROFIT_KEYWORDS:
        if kw in text:
            score += 40
            break

    for kw in ACTION_KEYWORDS:
        if kw in text:
            score += 15
            break

    for kw in PLATFORM_KEYWORDS:
        if kw in html_raw:
            score += 25
            break

    # Target criteria: Score kam az kam 80 ho
    if score >= 80:
        return {
            "domain": domain,
            "score": score,
            "payments": list(set(detected_payments)),
            "detected_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    return None

def main():
    domains = get_recent_domains("top")
    print(f"[*] Found {len(domains)} candidates. Scanning content...")
    
    matched_sites = []
    for d in domains:
        result = analyze_site(d)
        if result:
            print(f"[✔] MATCH FOUND: {d} (Score: {result['score']})")
            matched_sites.append(result)
        time.sleep(1) # Polite delay
        
    os.makedirs("data", exist_ok=True)
    with open("data/results.json", "w") as f:
        json.dump(matched_sites, f, indent=4)
    print(f"[*] Saved {len(matched_sites)} targets to data/results.json")

if __name__ == "__main__":
    main()
