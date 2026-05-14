# 🤖 Bot Referral Zealy - Injective

Bot Python untuk auto-register akun Zealy via referral link menggunakan **Gmail + 2captcha**.

---

## 📋 Requirement

- Python 3.8+
- Gmail account (untuk generate alias per akun)
- [2captcha.com](https://2captcha.com) API key (untuk solve Turnstile)
- Saldo 2captcha minimal $1 (~333 akun @ $0.003/solve)

---

## ⚙️ Setup

### 1. Clone repository

```bash
git clone https://github.com/zean6178/Bot-Reff-Zeally.git
cd Bot-Reff-Zeally
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Gmail IMAP

1. Buka [Gmail Settings](https://mail.google.com) → Settings → See all settings
2. Tab **Forwarding and POP/IMAP** → **Enable IMAP** → Save Changes
3. Buka [myaccount.google.com/security](https://myaccount.google.com/security)
4. Klik **2-Step Verification** → aktifkan dulu
5. Scroll bawah → **App passwords** → ketik `ZealyBot` → **Generate**
6. Copy **16 karakter** App Password yang muncul

### 4. Daftar 2captcha

1. Daftar di [2captcha.com](https://2captcha.com)
2. Isi saldo minimal $1
3. Copy API key dari dashboard

### 5. Konfigurasi

Edit `config.py` dan isi:

```python
# Gmail kamu
GMAIL_ADDRESS      = "emailkamu@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # 16 karakter App Password

# 2captcha API key
TWOCAPTCHA_API_KEY = "your_2captcha_api_key"

# Jumlah akun yang ingin dibuat
NUM_ACCOUNTS = 5
```

### 6. Isi Twitter username

Edit `twitter_accounts.txt` dan isi username Twitter kamu (1 per baris, tanpa @):

```
namatwitter1
namatwitter2
```

> ⚠️ **Syarat Twitter:** Akun berumur minimal **90 hari** & punya minimal **100 followers**

---

## 🚀 Menjalankan Bot

```bash
python3 main.py
```

---

## 🔄 Flow Bot

```
Untuk setiap akun:
  1. 📧 Generate Gmail alias: emailkamu+abc123@gmail.com
  2. 🔐 Solve Cloudflare Turnstile via 2captcha (~15 detik)
  3. 📨 Kirim OTP ke alias tersebut
  4. 📬 Baca OTP dari Gmail inbox via IMAP
  5. 🔑 Verify OTP ke Zealy → dapat JWT token
  6. 👤 Set username akun
  7. 🔗 Join komunitas via invite link
  8. 🎯 Auto-claim quest yang tersedia
  9. 💾 Simpan hasil ke results.txt
```

---

## 📁 Struktur File

```
Bot-Reff-Zeally/
├── main.py              ← Entry point, jalankan ini
├── zealy_bot.py         ← Core Zealy bot logic
├── mail_tm.py           ← Gmail alias + IMAP handler
├── captcha_solver.py    ← 2captcha Turnstile solver
├── config.py            ← Semua konfigurasi ← EDIT INI
├── twitter_accounts.txt ← Daftar Twitter username ← ISI INI
├── results.txt          ← Output hasil (auto-generated)
├── generated_accounts.txt ← Info akun yang dibuat (auto-generated)
└── requirements.txt     ← Dependencies
```

---

## 📊 Output

**results.txt:**
```
[2024-01-01 20:00:00] Email: abc@gmail.com | Twitter: user1 | Status: success | XP: 10 | Selesai! 3 quest claimed
```

**generated_accounts.txt:**
```
[2024-01-01 20:00:00] email=abc@gmail.com | pass=dummy | twitter=user1
```

---

## ⚙️ Konfigurasi Lanjutan

| Parameter | Default | Keterangan |
|---|---|---|
| `NUM_ACCOUNTS` | 5 | Jumlah akun yang dibuat |
| `DELAY_BETWEEN_ACCOUNTS` | 120 | Delay antar akun (detik) |
| `DELAY_BETWEEN_REQUESTS` | 2 | Delay antar request API |
| `EMAIL_WAIT_TIMEOUT` | 90 | Timeout tunggu OTP (detik) |
| `CAPTCHA_SOLVE_TIMEOUT` | 120 | Timeout 2captcha (detik) |

---

## 🔧 Troubleshooting

| Error | Penyebab | Solusi |
|---|---|---|
| `IMAP login gagal` | App Password salah | Pastikan IMAP aktif & App Password benar |
| `Disposable emails not allowed` | Domain email di-blacklist | Sudah fix: pakai Gmail alias |
| `OTP is wrong or expired` | OTP expire sebelum verify | Bot sudah fix: verify langsung tanpa delay |
| `Account not found` | Email alias vs base email mismatch | Sudah fix: verify pakai base email |
| `Too many requests 429` | Rate limit per email per jam | Tunggu 1 jam atau pakai email berbeda |
| `Turnstile FORBIDDEN` | IP di-block Cloudflare | Pakai proxy atau ganti IP |
| `git pull conflict` | config.py lokal vs GitHub | Run: `git stash && git pull && git stash pop` |

---

## 💡 Tips

- **Untuk hindari rate limit:** Gunakan `DELAY_BETWEEN_ACCOUNTS = 120` (2 menit)
- **Gmail alias:** Setiap akun pakai alias unik `email+TAG@gmail.com` — unlimited tanpa rate limit
- **Proxy:** Tambahkan proxy di `PROXIES` di `config.py` untuk avoid IP ban
- **Quest Twitter:** Butuh akun Twitter 90 hari + 100 followers — isi di `twitter_accounts.txt`

---

## ⚠️ Disclaimer

Bot ini dibuat untuk keperluan edukasi. Penggunaan bot dapat melanggar Terms of Service platform. Gunakan dengan bijak dan risiko ditanggung sendiri.
