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
    TWOCAPTCHA_API_KEY,
)
from zealy_bot import ZealyBot
from mail_tm import MailTM
from captcha_solver import CaptchaSolver

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
                    usernames.append(line.lstrip("@"))
        log.info(f"✅ Loaded {len(usernames)} Twitter username")
    except FileNotFoundError:
        log.warning(f"⚠️ File '{filepath}' tidak ditemukan.")
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
    log.info(f"💾 Disimpan ke {filepath}")


def save_account_info(email: str, email_pass: str, twitter: str,
                      filepath: str = "generated_accounts.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath, "a") as f:
        f.write(f"[{timestamp}] email={email} | pass={email_pass} | twitter={twitter}\n")


def print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║   ZEALY REFERRAL BOT  —  2captcha Turnstile Solver   ║
║   Platform : Injective  |  mail.tm + 2captcha.com    ║
╚══════════════════════════════════════════════════════╝
""")


def check_api_key():
    """Cek saldo 2captcha sebelum mulai"""
    if TWOCAPTCHA_API_KEY == "YOUR_2CAPTCHA_API_KEY_HERE":
        log.error("❌ TWOCAPTCHA_API_KEY belum diisi di config.py!")
        return False
    solver = CaptchaSolver()
    balance = solver.check_balance()
    if balance <= 0:
        log.error(f"❌ Saldo 2captcha kosong atau API key salah!")
        return False
    log.info(f"💰 Saldo 2captcha: ${balance:.4f} — OK")
    return True


def process_account(i: int, total: int, twitter: str, proxy: str = None) -> dict:
    """
    Flow lengkap satu akun:
      1. Buat email temp (mail.tm)
      2. Solve Turnstile via 2captcha
      3. Kirim OTP ke email
      4. Baca OTP dari inbox mail.tm
      5. Verify OTP → dapat JWT
      6. Join komunitas & complete quest
    """
    failed = lambda msg: {
        "email": "N/A", "twitter": twitter,
        "status": "failed", "xp": 0, "message": msg
    }

    # ── 1. Buat email temp ──────────────────────────────
    log.info(f"[{i}/{total}] 📧 Membuat email temporary...")
    mail = MailTM()
    account_info = mail.create_account()
    if not account_info:
        return failed("Gagal buat email temp")

    email      = account_info["email"]
    email_pass = account_info["password"]
    log.info(f"[{i}/{total}] Email: {email} | Twitter: {twitter}")
    save_account_info(email, email_pass, twitter)

    bot = ZealyBot(email=email, twitter_username=twitter, proxy=proxy)

    # ── 2. Solve Turnstile via 2captcha ────────────────
    log.info(f"[{i}/{total}] 🔐 Solving Turnstile (2captcha)...")
    turnstile_token = bot.solve_turnstile()
    if not turnstile_token:
        return failed("Gagal solve Turnstile")

    # ── 3. Kirim OTP ke email ──────────────────────────
    log.info(f"[{i}/{total}] 📨 Mengirim OTP ke {email}...")
    if not bot.send_otp(turnstile_token):
        return failed("Gagal kirim OTP")

    # ── 4. Baca OTP dari inbox mail.tm ─────────────────
    log.info(f"[{i}/{total}] 📬 Menunggu OTP di inbox...")
    otp = mail.find_otp_code(max_wait=EMAIL_WAIT_TIMEOUT)
    if not otp:
        return failed("OTP tidak ditemukan di inbox")
    log.info(f"[{i}/{total}] 🔑 OTP: {otp}")

    # ── 5 & 6: Verify OTP, join, complete quest ────────
    result = bot.run(otp=otp, turnstile_token=turnstile_token)
    result["email"] = email
    return result


def main():
    print_banner()

    # Cek API key 2captcha
    if not check_api_key():
        return

    twitter_usernames = load_twitter_usernames(TWITTER_USERNAMES_FILE)
    if not twitter_usernames:
        log.error("❌ Tidak ada Twitter username! Isi twitter_accounts.txt dulu.")
        return

    log.info(f"🚀 Akan membuat {NUM_ACCOUNTS} akun baru...")
    log.info(f"📋 Output: {OUTPUT_FILE}")
    print("-" * 58)

    stats = {"success": 0, "partial": 0, "failed": 0}

    for i in range(1, NUM_ACCOUNTS + 1):
        print(f"\n{'='*58}")
        log.info(f"[{i}/{NUM_ACCOUNTS}] Memulai akun baru...")

        twitter = twitter_usernames[(i - 1) % len(twitter_usernames)]
        proxy   = random.choice(PROXIES) if PROXIES else None

        result = process_account(i, NUM_ACCOUNTS, twitter, proxy)

        status = result.get("status", "failed")
        stats[status] = stats.get(status, 0) + 1

        save_result(result, OUTPUT_FILE)
        emoji = {"success": "✅", "partial": "⚠️", "failed": "❌"}.get(status, "❓")
        log.info(f"{emoji} [{i}/{NUM_ACCOUNTS}] {result['email']} → {result['message']}")

        if i < NUM_ACCOUNTS:
            delay = DELAY_BETWEEN_ACCOUNTS + random.uniform(3, 7)
            log.info(f"⏳ Delay {delay:.1f}s...")
            time.sleep(delay)

    print("\n" + "=" * 58)
    print("📊 SUMMARY HASIL:")
    print(f"   ✅ Sukses  : {stats['success']} akun")
    print(f"   ⚠️  Partial : {stats.get('partial', 0)} akun")
    print(f"   ❌ Gagal   : {stats['failed']} akun")
    print(f"   📁 Detail  : {OUTPUT_FILE}")
    print("=" * 58)


if __name__ == "__main__":
    main()
