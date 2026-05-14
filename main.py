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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def load_twitter_usernames(filepath: str) -> list:
    """Load daftar Twitter username dari file"""
    usernames = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    usernames.append(line)
        log.info(f"✅ Loaded {len(usernames)} Twitter username")
    except FileNotFoundError:
        log.warning(f"⚠️ File '{filepath}' tidak ditemukan. Menggunakan username default.")
    return usernames


def save_result(result: dict, filepath: str):
    """Simpan hasil ke file output"""
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


def save_account_info(email: str, email_pass: str, zealy_pass: str, twitter: str, filepath: str = "generated_accounts.txt"):
    """Simpan info akun yang berhasil dibuat"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] email={email} | email_pass={email_pass} | zealy_pass={zealy_pass} | twitter={twitter}\n"
    with open(filepath, "a") as f:
        f.write(line)


def print_banner():
    banner = """
╔══════════════════════════════════════════════════╗
║      ZEALY REFERRAL BOT - AUTO EMAIL             ║
║      Platform: Injective | mail.tm               ║
╚══════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    print_banner()

    # Load Twitter usernames
    twitter_usernames = load_twitter_usernames(TWITTER_USERNAMES_FILE)

    log.info(f"🚀 Akan membuat {NUM_ACCOUNTS} akun baru...")
    log.info(f"📋 Output hasil: {OUTPUT_FILE}")
    print("-" * 55)

    results = {"success": 0, "partial": 0, "failed": 0}

    for i in range(1, NUM_ACCOUNTS + 1):
        log.info(f"\n{'='*55}")
        log.info(f"[{i}/{NUM_ACCOUNTS}] Membuat akun baru...")

        # Pilih Twitter username
        if twitter_usernames:
            twitter = twitter_usernames[(i - 1) % len(twitter_usernames)]
        else:
            twitter = f"user_{random.randint(10000, 99999)}"

        # Pilih proxy secara acak jika ada
        proxy = random.choice(PROXIES) if PROXIES else None

        # ─── STEP 1: Generate email temp via mail.tm ───
        log.info(f"[{i}] 📧 Membuat email temporary...")
        mail = MailTM()
        account_info = mail.create_account()

        if not account_info:
            log.error(f"[{i}] ❌ Gagal buat email, skip akun ini")
            results["failed"] += 1
            continue

        temp_email = account_info["email"]
        temp_email_pass = account_info["password"]

        # Password untuk akun Zealy (bisa sama atau beda)
        zealy_password = account_info["password"]

        log.info(f"[{i}] 📧 Email: {temp_email} | Twitter: {twitter}")

        # ─── STEP 2: Jalankan Zealy bot ───
        bot = ZealyBot(
            email=temp_email,
            password=zealy_password,
            twitter_username=twitter,
            proxy=proxy
        )

        # Register dulu (sebelum cek verifikasi email)
        registered = bot.register()

        if not registered:
            log.error(f"[{i}] ❌ Gagal register di Zealy")
            results["failed"] += 1
            save_result({
                "email": temp_email,
                "twitter": twitter,
                "status": "failed",
                "xp": 0,
                "message": "Gagal register di Zealy"
            }, OUTPUT_FILE)
            time.sleep(DELAY_BETWEEN_ACCOUNTS)
            continue

        # ─── STEP 3: Cek inbox untuk link verifikasi ───
        log.info(f"[{i}] 📬 Menunggu email verifikasi dari Zealy...")
        verification_link = mail.find_verification_link(max_wait=EMAIL_WAIT_TIMEOUT)

        if verification_link:
            bot.verify_email(verification_link)
        else:
            log.warning(f"[{i}] ⚠️ Link verifikasi tidak ditemukan, lanjut tanpa verifikasi")

        # ─── STEP 4: Join komunitas & complete quest ───
        time.sleep(2)
        result = bot.run(verification_link=verification_link)

        # Update statistik
        status = result.get("status", "failed")
        results[status] = results.get(status, 0) + 1

        # Simpan hasil
        save_result(result, OUTPUT_FILE)
        save_account_info(temp_email, temp_email_pass, zealy_password, twitter)

        # Log hasil
        emoji = {"success": "✅", "partial": "⚠️", "failed": "❌"}.get(status, "❓")
        log.info(f"{emoji} [{i}/{NUM_ACCOUNTS}] {temp_email} → {result['message']}")

        # Cleanup email temp (opsional, comment jika ingin keep)
        # mail.delete_account()

        # Delay sebelum akun berikutnya
        if i < NUM_ACCOUNTS:
            delay = DELAY_BETWEEN_ACCOUNTS + random.uniform(2, 5)
            log.info(f"⏳ Delay {delay:.1f}s sebelum akun berikutnya...")
            time.sleep(delay)

    # ─── SUMMARY ───
    print("\n" + "=" * 55)
    print("📊 SUMMARY HASIL:")
    print(f"   ✅ Sukses    : {results['success']} akun")
    print(f"   ⚠️  Partial   : {results.get('partial', 0)} akun")
    print(f"   ❌ Gagal     : {results['failed']} akun")
    print(f"   📁 Detail    : {OUTPUT_FILE}")
    print(f"   📁 Akun info : generated_accounts.txt")
    print("=" * 55)


if __name__ == "__main__":
    main()
