"""
Script untuk test domain mana yang tidak di-blacklist Zealy.
Jalankan sekali: python3 test_domains.py
"""
import requests
import time

# Ambil semua domain dari mail.tm
resp = requests.get("https://api.mail.tm/domains")
data = resp.json()
if isinstance(data, list):
    mailtm_domains = [d["domain"] for d in data if "domain" in d]
else:
    mailtm_domains = [d["domain"] for d in data.get("hydra:member", []) if "domain" in d]

print(f"Domain dari mail.tm: {mailtm_domains}")
print()

# Domain alternatif lainnya
extra_domains = [
    "guerrillamail.com",
    "sharklasers.com",
    "grr.la",
    "yopmail.com",
    "mailnull.com",
    "spamgourmet.com",
    "trashmail.com",
    "temp-mail.org",
    "fakeinbox.com",
    "dispostable.com",
    "mailforspam.com",
    "getairmail.com",
    "spamgourmet.net",
    "throwam.com",
    "moakt.cc",
    "moakt.co",
    "fakemail.net",
    "tempmailo.com",
    "emltmp.com",
    "tmailor.com",
]

all_domains = mailtm_domains + extra_domains

print("Testing domain mana yang tidak di-blacklist Zealy...")
print("=" * 60)

allowed = []
blocked = []

for domain in all_domains:
    email = f"testzealy777@{domain}"
    try:
        resp = requests.post(
            "https://api-v2.zealy.io/api/authentication/otp/send",
            json={
                "email": email,
                "turnstileToken": "test_token_for_domain_check",
            },
            headers={
                "Content-Type": "application/json",
                "Origin": "https://zealy.io",
                "Referer": "https://zealy.io/sign-up",
            },
            timeout=10
        )
        data = resp.json()
        msg = data.get("message", "")

        if "Disposable" in msg or "disposable" in msg:
            print(f"❌ BLOCKED   | {domain}")
            blocked.append(domain)
        elif resp.status_code in [200, 201, 202]:
            print(f"✅ ALLOWED   | {domain}")
            allowed.append(domain)
        elif "captcha" in msg.lower() or "human" in msg.lower() or resp.status_code == 401:
            # Captcha error = domain OK tapi token dummy kita invalid — domain ALLOWED!
            print(f"✅ ALLOWED   | {domain} (captcha check = domain valid)")
            allowed.append(domain)
        elif resp.status_code == 400 and "email" in msg.lower():
            print(f"❌ BLOCKED   | {domain} | {msg[:60]}")
            blocked.append(domain)
        else:
            print(f"⚠️  UNKNOWN   | {domain} | {resp.status_code} | {msg[:60]}")

        time.sleep(0.5)

    except Exception as e:
        print(f"⚠️  ERROR     | {domain} | {e}")

print()
print("=" * 60)
print(f"✅ ALLOWED ({len(allowed)}): {allowed}")
print(f"❌ BLOCKED ({len(blocked)}): {blocked}")

if allowed:
    print()
    print("Masukkan domain berikut ke mail_tm.py ALLOWED_DOMAINS:")
    print(allowed)
