# ============================================================
#  KONFIGURASI BOT ZEALY REFERRAL
# ============================================================

# Invite link referral kamu
INVITE_LINK = "https://zealy.io/c/injectivemissions/invite/CJ75OjMext_T3VVKdsG2U?questId=49a858f9-b0c5-4e23-9b72-a1361f1e2d0c"

# Community subdomain Zealy
COMMUNITY_SUBDOMAIN = "injectivemissions"

# ─────────────────────────────────────────────
#  MAILSLURP API KEY  ← ISI INI
# ─────────────────────────────────────────────
# Daftar gratis di: https://mailslurp.com
# Dashboard → API Keys → Copy key
MAILSLURP_API_KEY = "YOUR_MAILSLURP_API_KEY_HERE"

# Gmail settings for email alias
GMAIL_ADDRESS      = "alvaomegazr@gmail.com"
GMAIL_APP_PASSWORD = "YOUR_APP_PASSWORD_HERE"  # Get from: https://myaccount.google.com/apppasswords

# ─────────────────────────────────────────────
#  2CAPTCHA API KEY  ← ISI INI
# ─────────────────────────────────────────────
# Daftar & isi saldo di: https://2captcha.com
TWOCAPTCHA_API_KEY = "YOUR_2CAPTCHA_API_KEY_HERE"

# Cloudflare Turnstile site key milik Zealy
# (didapat dari source HTML zealy.io/sign-up)
TURNSTILE_SITE_KEY = "0x4AAAAAAA9xxWmJYaOq_CNN"
TURNSTILE_PAGE_URL = "https://zealy.io/sign-up"

# ─────────────────────────────────────────────
#  PENGATURAN UTAMA
# ─────────────────────────────────────────────

# Jumlah akun yang ingin dibuat
NUM_ACCOUNTS = 5

# File berisi daftar Twitter username (1 per baris)
TWITTER_USERNAMES_FILE = "twitter_accounts.txt"

# ─────────────────────────────────────────────
#  DELAY SETTINGS
# ─────────────────────────────────────────────

# Delay antar akun (detik)
DELAY_BETWEEN_ACCOUNTS = 10

# Delay antar request (detik)
DELAY_BETWEEN_REQUESTS = 2

# Timeout tunggu email verifikasi (detik)
EMAIL_WAIT_TIMEOUT = 90

# Timeout tunggu 2captcha solve (detik)
CAPTCHA_SOLVE_TIMEOUT = 120

# ─────────────────────────────────────────────
#  FILE OUTPUT
# ─────────────────────────────────────────────
OUTPUT_FILE = "results.txt"

# ─────────────────────────────────────────────
#  PROXY (OPSIONAL)
# ─────────────────────────────────────────────
# Format: "http://user:pass@host:port"
PROXIES = [
    # "http://user:pass@192.168.1.1:8080",
]

# ─────────────────────────────────────────────
#  USER AGENT
# ─────────────────────────────────────────────
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
