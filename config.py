# ============================================================
#  KONFIGURASI BOT ZEALY REFERRAL
# ============================================================

# Invite link referral kamu
INVITE_LINK = "https://zealy.io/c/injectivemissions/invite/CJ75OjMext_T3VVKdsG2U?questId=49a858f9-b0c5-4e23-9b72-a1361f1e2d0c"

# Community subdomain Zealy
COMMUNITY_SUBDOMAIN = "injectivemissions"

# Zealy API base URL
ZEALY_API_BASE = "https://api.zealy.io"

# ─────────────────────────────────────────────
#  PENGATURAN UTAMA
# ─────────────────────────────────────────────

# Jumlah akun yang ingin dibuat
NUM_ACCOUNTS = 5

# File berisi daftar Twitter username (1 per baris)
# Kosongkan string jika mau pakai username random
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

# ─────────────────────────────────────────────
#  FILE OUTPUT
# ─────────────────────────────────────────────

# File output hasil run
OUTPUT_FILE = "results.txt"

# ─────────────────────────────────────────────
#  PROXY (OPSIONAL)
# ─────────────────────────────────────────────
# Format: "http://user:pass@host:port" atau "http://host:port"
# Kosongkan list [] jika tidak pakai proxy
PROXIES = [
    # "http://user:pass@192.168.1.1:8080",
]

# ─────────────────────────────────────────────
#  USER AGENT
# ─────────────────────────────────────────────
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
