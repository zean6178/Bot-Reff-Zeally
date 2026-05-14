# 🤖 Bot Referral Zealy - Injective

Bot Python untuk auto-register & complete quest di Zealy via referral link.

## 📋 Syarat

- Python 3.8+
- Akun Twitter/X yang:
  - Berumur minimal **90 hari**
  - Punya minimal **100 followers**
- Email untuk daftar Zealy

## ⚙️ Instalasi

```bash
# 1. Clone / download project
cd Bot-Reff-Zeally

# 2. Install dependencies
pip install -r requirements.txt
```

## 🛠️ Konfigurasi

### 1. Edit `accounts.txt`
Isi dengan akun kamu, format:
```
email:password:twitter_username
```
Contoh:
```
johndoe@gmail.com:MyPassword123:johndoe_twitter
janedoe@gmail.com:SecurePass456:janedoe_twitter
```

### 2. Edit `config.py` (opsional)
- `DELAY_BETWEEN_ACCOUNTS` — delay antar akun (default: 5 detik)
- `DELAY_BETWEEN_REQUESTS` — delay antar request (default: 2 detik)
- `PROXIES` — tambahkan proxy jika butuh (opsional)

## 🚀 Cara Pakai

```bash
python main.py
```

## 📊 Output

Hasil akan tersimpan di `results.txt`:
```
[2024-01-01 12:00:00] email@gmail.com | Twitter: user | Status: success | XP: 10 | Selesai! Complete 3 quest
```

## 📁 Struktur File

```
Bot-Reff-Zeally/
├── main.py          # Entry point, jalankan ini
├── zealy_bot.py     # Core bot logic
├── config.py        # Konfigurasi
├── accounts.txt     # Daftar akun (isi sendiri)
├── results.txt      # Output hasil (auto-generated)
└── requirements.txt # Dependencies
```

## ⚠️ Disclaimer

Bot ini dibuat untuk keperluan edukasi. Penggunaan bot pada platform dapat melanggar Terms of Service. Gunakan dengan bijak dan risiko ditanggung sendiri.
