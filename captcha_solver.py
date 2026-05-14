import time
import requests
import logging
from config import (
    TWOCAPTCHA_API_KEY,
    TURNSTILE_SITE_KEY,
    TURNSTILE_PAGE_URL,
    CAPTCHA_SOLVE_TIMEOUT,
)

log = logging.getLogger(__name__)

TWOCAPTCHA_IN  = "https://api.2captcha.com/in.php"
TWOCAPTCHA_RES = "https://api.2captcha.com/res.php"


class CaptchaSolver:
    """
    Solve Cloudflare Turnstile via 2captcha.com API.

    Harga: ~$2-3 per 1000 solve (sangat murah).
    Daftar & isi saldo di: https://2captcha.com
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or TWOCAPTCHA_API_KEY

    def solve_turnstile(self, site_key: str = None, page_url: str = None) -> str:
        """
        Solve Cloudflare Turnstile dan return token.

        Args:
            site_key: Turnstile site key (default dari config)
            page_url: URL halaman (default dari config)

        Returns:
            str: Token hasil solve, atau "" jika gagal
        """
        site_key = site_key or TURNSTILE_SITE_KEY
        page_url = page_url or TURNSTILE_PAGE_URL

        log.info(f"🔐 Mengirim Turnstile ke 2captcha...")

        # Step 1: Submit captcha
        captcha_id = self._submit(site_key, page_url)
        if not captcha_id:
            return ""

        log.info(f"🔐 Captcha ID: {captcha_id} — menunggu solve...")

        # Step 2: Poll hasil
        token = self._poll(captcha_id)
        if token:
            log.info(f"✅ Turnstile solved! Token: {token[:30]}...")
        else:
            log.error("❌ Gagal solve Turnstile")

        return token

    def _submit(self, site_key: str, page_url: str) -> str:
        """Submit captcha ke 2captcha, return captcha ID"""
        try:
            resp = requests.post(TWOCAPTCHA_IN, data={
                "key":      self.api_key,
                "method":   "turnstile",
                "sitekey":  site_key,
                "pageurl":  page_url,
                "json":     1,
            }, timeout=30)

            data = resp.json()
            if data.get("status") == 1:
                return str(data.get("request", ""))
            else:
                log.error(f"❌ 2captcha submit error: {data}")
                return ""

        except Exception as e:
            log.error(f"❌ Error submit captcha: {e}")
            return ""

    def _poll(self, captcha_id: str) -> str:
        """Poll 2captcha sampai dapat token (atau timeout)"""
        elapsed = 0
        interval = 5   # cek setiap 5 detik
        initial_wait = 15  # tunggu 15 detik sebelum cek pertama

        time.sleep(initial_wait)
        elapsed += initial_wait

        while elapsed < CAPTCHA_SOLVE_TIMEOUT:
            try:
                resp = requests.get(TWOCAPTCHA_RES, params={
                    "key":    self.api_key,
                    "action": "get",
                    "id":     captcha_id,
                    "json":   1,
                }, timeout=15)

                data = resp.json()

                if data.get("status") == 1:
                    return data.get("request", "")

                if data.get("request") == "CAPCHA_NOT_READY":
                    log.info(f"⏳ Captcha belum selesai... ({elapsed}s)")
                    time.sleep(interval)
                    elapsed += interval
                    continue

                # Error lain
                log.error(f"❌ 2captcha poll error: {data}")
                return ""

            except Exception as e:
                log.error(f"❌ Error poll captcha: {e}")
                time.sleep(interval)
                elapsed += interval

        log.error(f"❌ Captcha timeout setelah {CAPTCHA_SOLVE_TIMEOUT}s")
        return ""

    def check_balance(self) -> float:
        """Cek saldo 2captcha"""
        try:
            resp = requests.get(TWOCAPTCHA_RES, params={
                "key":    self.api_key,
                "action": "getbalance",
                "json":   1,
            }, timeout=10)
            data = resp.json()
            if data.get("status") == 1:
                balance = float(data.get("request", 0))
                log.info(f"💰 Saldo 2captcha: ${balance:.4f}")
                return balance
            else:
                log.error(f"❌ Cek saldo gagal: {data}")
                return 0.0
        except Exception as e:
            log.error(f"❌ Error cek saldo: {e}")
            return 0.0
