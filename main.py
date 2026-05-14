import time
import random
import logging
from datetime import datetime
from config import (
    ACCOUNTS_FILE,
    OUTPUT_FILE,
    DELAY_BETWEEN_ACCOUNTS,
    PROXIES
)
from zealy_bot import ZealyBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def load_accounts(filepath: str) -> list:
    """Load akun dari file accounts.txt"""
    accounts = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                # Skip komentar dan baris kosong
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) >= 3:
                    email = parts[0].strip()
                    password = parts[1].strip()
                    twitter = parts[2].strip()
                    accounts.append({
                        "email": email,
                        "password": password,
                        "twitter": twitter
                    })
        log.info(f"✅ Berhasil load {len(accounts)} akun dari {filepath}")
    except FileNotFoundError:
        log.error(f"❌ File '{filepath}' tidak ditemukan!")
    except Exception as e:
        log.error(f"❌ Error membaca file akun: {e}")
    return accounts


def save_result(result: dict, filepath: str):
    """Simpan hasil ke file output"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {result['email']} | Twitter: {result['twitter']} | Status: {result['status']} | XP: {result['xp']} | {result['message']}\n"
    with open(filepath, "a") as f:
        f.write(line)


def print_banner():
    banner = """
╔══════════════════════════════════════════════╗
║        ZEALY REFERRAL BOT - Injective        ║
║          by Bot-Reff-Zeally                  ║
╚══════════════════════════════════════════════╝
"""
    print(banner)


def main():
    print_banner()

    # Load akun
    accounts = load_accounts(ACCOUNTS_FILE)
    if not accounts:
        log.error("❌ Tidak ada akun yang bisa diproses. Periksa accounts.txt")
        return

    log.info(f"🚀 Memulai proses {len(accounts)} akun...")
    log.info(f"📋 Output akan disimpan ke: {OUTPUT_FILE}")
    print("-" * 50)

    results = {
        "success": 0,
        "partial": 0,
        "failed": 0
    }

    for i, account in enumerate(accounts, 1):
        log.info(f"\n[{i}/{len(accounts)}] Memproses akun: {account['email']}")

        # Pilih proxy secara acak jika ada
        proxy = None
        if PROXIES:
            proxy = random.choice(PROXIES)

        # Jalankan bot untuk akun ini
        bot = ZealyBot(
            email=account["email"],
            password=account["password"],
            twitter_username=account["twitter"],
            proxy=proxy
        )

        result = bot.run()

        # Update statistik
        results[result["status"]] = results.get(result["status"], 0) + 1

        # Simpan hasil
        save_result(result, OUTPUT_FILE)

        # Log hasil
        status_emoji = {"success": "✅", "partial": "⚠️", "failed": "❌"}
        emoji = status_emoji.get(result["status"], "❓")
        log.info(f"{emoji} [{i}/{len(accounts)}] {result['email']} → {result['message']}")

        # Delay sebelum akun berikutnya
        if i < len(accounts):
            delay = DELAY_BETWEEN_ACCOUNTS + random.uniform(1, 3)
            log.info(f"⏳ Menunggu {delay:.1f} detik sebelum akun berikutnya...")
            time.sleep(delay)

    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY HASIL:")
    print(f"   ✅ Sukses   : {results['success']} akun")
    print(f"   ⚠️  Partial  : {results.get('partial', 0)} akun")
    print(f"   ❌ Gagal    : {results['failed']} akun")
    print(f"   📁 Detail   : {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
