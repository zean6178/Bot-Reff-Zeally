import time
import random
import logging
from datetime import datetime
from config import (
    OUTPUT_FILE,
    DELAY_BETWEEN_ACCOUNTS,
    PROXIES,
    NUM_ACCOUNTS,
    TWITTER_USERNAMES_FILE,
    EMAIL_WAIT_TIMEOUT,
)
from zealy_bot import ZealyBot
from mail_tm import MailTM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def load_twitter_usernames(filepath: str) -> list:
    usernames = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Hapus @ jika ada
                    usernames.append(line.lstrip("@"))
        log.info(f"✅ Loaded {len(usernames)} Twitter username")
    except FileNotFoundError:
        log.warning(f"⚠️ File '{filepath}' tidak ditemukan. Pakai username random.")
    return usernames


def save_result(result: dict, filepath: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"[{timestamp}] "
        f"Email: {result['email']} | "
        f"Twitter: {result['twitter']} | "
        f"Status: {result['status']} | "
        f"XP: {result['xp']} | "
        f"{result['message']}\n"
    )
    with open(filepath, "a") as f:
        f.write(line)
    log.info(f"💾 Hasil disimpan ke {filepath}")


def save_account_info(email: str, email_pass: str, twitter: str, filepath: str = "generated_accounts.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] email={email} | email_pass={email_pass} | twitter={twitter}\n"
    with open(filepath, "a") as f:
        f.write(line)


def print_banner():
    print("""
╔══════════════════════════════════════════════════╗
║    ZEALY REFERRAL BOT  —  OTP Email Flow         ║
║    Platform : Injective | mail.tm                ║
╚══════════════════════════════════════════════════╝
""")


def process_account(i: int, total: int, twitter: str, proxy: str = None) -> dict:
    """
    Proses satu akun dengan flow:
      1. Buat email temp (mail.tm)
      2. Kirim OTP via Zealy
      3. Baca OTP dari inbox
      4. Verify OTP → join & complete quest
    """
    failed = lambda msg: {
        "email": "N/A",
        "twitter": twitter,
        "status": "failed",
        "xp": 0,
        "message": msg
    }

    # ── 1. Buat email temp ──────────────────────────
    log.info(f"[{i}/{total}] 📧 Membuat email temporary...")
    mail = MailTM()
    account_info = mail.create_account()

    if not account_info:
        return failed("Gagal buat email temp")

    email      = account_info["email"]
    email_pass = account_info["password"]
    log.info(f"[{i}/{total}] Email: {email} | Twitter: {twitter}")

    # Simpan info akun
    save_account_info(email, email_pass, twitter)

    # ── 2. Kirim OTP ke email via Zealy ─────────────
    bot = ZealyBot(email=email, twitter_username=twitter, proxy=proxy)

    if not bot.send_otp():
        # OTP endpoint belum ditemukan → coba log raw response untuk debug
        log.warning(f"[{i}/{total}] ⚠️ send_otp gagal — mungkin flow berbeda, cek debug log")
        return failed("Gagal kirim OTP — endpoint belum ditemukan")

    # ── 3. Tunggu OTP di inbox ───────────────────────
    log.info(f"[{i}/{total}] ⏳ Menunggu OTP di inbox {email}...")
    otp = mail.find_otp_code(max_wait=EMAIL_WAIT_TIMEOUT)

    if not otp:
        log.warning(f"[{i}/{total}] ⚠️ OTP tidak ditemukan — coba cari verification link...")
        # Fallback: coba verification link
        link = mail.find_verification_link(max_wait=30)
        if link:
            log.info(f"[{i}/{total}] 🔗 Ditemukan verification link, klik...")
            import requests as req
            try:
                req.get(link, allow_redirects=True, timeout=10)
                log.info(f"[{i}/{total}] ✅ Link verifikasi di-klik")
            except Exception as e:
                log.error(f"[{i}/{total}] ❌ Gagal klik link: {e}")
        return failed("OTP tidak ditemukan di inbox")

    # ── 4. Verify OTP & jalankan bot ────────────────
    result = bot.run_after_otp(otp)
    result["email"] = email
    return result


def main():
    print_banner()

    twitter_usernames = load_twitter_usernames(TWITTER_USERNAMES_FILE)
    log.info(f"🚀 Akan membuat {NUM_ACCOUNTS} akun baru...")
    log.info(f"📋 Output: {OUTPUT_FILE}")
    print("-" * 55)

    stats = {"success": 0, "partial": 0, "failed": 0}

    for i in range(1, NUM_ACCOUNTS + 1):
        print(f"\n{'='*55}")
        log.info(f"[{i}/{NUM_ACCOUNTS}] Memulai akun baru...")

        # Pilih Twitter username
        twitter = twitter_usernames[(i - 1) % len(twitter_usernames)] if twitter_usernames \
                  else f"user{random.randint(10000, 99999)}"

        # Pilih proxy
        proxy = random.choice(PROXIES) if PROXIES else None

        result = process_account(i, NUM_ACCOUNTS, twitter, proxy)

        # Update statistik
        status = result.get("status", "failed")
        stats[status] = stats.get(status, 0) + 1

        # Simpan & log hasil
        save_result(result, OUTPUT_FILE)
        emoji = {"success": "✅", "partial": "⚠️", "failed": "❌"}.get(status, "❓")
        log.info(f"{emoji} [{i}/{NUM_ACCOUNTS}] {result['email']} → {result['message']}")

        # Delay sebelum akun berikutnya
        if i < NUM_ACCOUNTS:
            delay = DELAY_BETWEEN_ACCOUNTS + random.uniform(2, 5)
            log.info(f"⏳ Delay {delay:.1f}s sebelum akun berikutnya...")
            time.sleep(delay)

    # Summary
    print("\n" + "=" * 55)
    print("📊 SUMMARY HASIL:")
    print(f"   ✅ Sukses    : {stats['success']} akun")
    print(f"   ⚠️  Partial   : {stats.get('partial', 0)} akun")
    print(f"   ❌ Gagal     : {stats['failed']} akun")
    print(f"   📁 Detail    : {OUTPUT_FILE}")
    print(f"   📁 Akun info : generated_accounts.txt")
    print("=" * 55)


if __name__ == "__main__":
    main()
