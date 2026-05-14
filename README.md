# 🤖 Bot Referral Zealy - Injective

Bot Python untuk **auto-generate email** & **auto-register** akun Zealy via referral link menggunakan **mail.tm** sebagai temp email provider.

## 📋 Fitur

- ✅ **Auto-generate email** temporary via mail.tm API
- ✅ **Auto-register** akun Zealy pakai email temp
- ✅ **Auto-cek inbox** & klik link verifikasi email
- ✅ **Auto-join** komunitas via invite/referral link
- ✅ **Auto-complete quest** yang bisa di-automate
- ✅ **Support proxy** (opsional)
- ✅ **Simpan hasil** ke file output
- ✅ **Simpan info akun** yang berhasil dibuat

## ⚙️ Instalasi

```bash
# Install dependencies
pip install -r requirements.txt
```

## 🛠️ Konfigurasi

### 1. Edit `config.py`
```python
NUM_ACCOUNTS = 5          # Jumlah akun yang ingin dibuat
EMAIL_WAIT_TIMEOUT = 90   # Timeout tunggu email verifikasi (detik)
DELAY_BETWEEN_ACCOUNTS = 10  # Delay antar akun (detik)
```

### 2. Edit `twitter_accounts.txt`
Isi dengan Twitter/X username yang memenuhi syarat:
```
# Tanpa @, 1 per baris
johndoe_twitter
janedoe_twitter
```

> ⚠️ **Syarat Twitter:** Akun berumur minimal **90 hari** & punya minimal **100 followers**

### 3. Proxy (Opsional)
Edit `config.py`:
```python
PROXIES = [
    "http://user:pass@host:port",
]
```

## 🚀 Cara Pakai

```bash
python main.py
```

## 📊 Flow Bot

```
Untuk setiap akun:
  1. 📧 Generate email temp via mail.tm
  2. 📝 Register akun Zealy dengan email tersebut
  3. 📬 Tunggu & ambil email verifikasi dari inbox
  4. ✅ Klik link verifikasi otomatis
  5. 🔗 Join komunitas via invite link kamu
  6. 🎯 Auto-complete quest yang tersedia
  7. 📊 Cek XP & simpan hasil
```

## 📁 Struktur File

```
Bot-Reff-Zeally/
├── main.py                  ← Entry point, jalankan ini
├── zealy_bot.py             ← Core Zealy bot logic
├── mail_tm.py               ← Handler temp email (mail.tm)
├── config.py                ← Semua konfigurasi
├── twitter_accounts.txt     ← Daftar Twitter username
├── results.txt              ← Output hasil (auto-generated)
├── generated_accounts.txt   ← Info akun yang dibuat (auto-generated)
└── requirements.txt         ← Dependencies
```

## 📄 Output

**results.txt:**
```
[2024-01-01 12:00:00] Email: abc@dcctb.com | Twitter: user1 | Status: success | XP: 10 | Selesai! Complete 3 quest
```

**generated_accounts.txt:**
```
[2024-01-01 12:00:00] email=abc@dcctb.com | email_pass=pass123 | zealy_pass=pass123 | twitter=user1
```

## ⚠️ Disclaimer

Bot ini dibuat untuk keperluan edukasi. Penggunaan bot dapat melanggar Terms of Service platform. Gunakan dengan bijak dan risiko ditanggung sendiri.
