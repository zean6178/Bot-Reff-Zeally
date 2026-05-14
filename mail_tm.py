import re
import requests
import time
import random
import string
import logging

log = logging.getLogger(__name__)

TEMPMAIL_LOL_API = "https://api.tempmail.lol"


class MailTM:
    """
    Email provider menggunakan tempmail.lol API.
    Domain-nya (misal: bhh.26ai.org, lc.dogmrp.com, dll) TIDAK di-blacklist Zealy.
    API gratis, no signup, generate & baca inbox via token.
    """

    def __init__(self):
        self.email    = None
        self.password = None
        self._token   = None

    def _random_string(self, length: int = 10) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    def create_account(self) -> dict:
        """Generate email baru via tempmail.lol"""
        try:
            resp = requests.get(
                f"{TEMPMAIL_LOL_API}/generate",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            data = resp.json()

            self.email   = data.get("address", "")
            self._token  = data.get("token", "")
            self.password = self._random_string(12)

            if not self.email or not self._token:
                raise ValueError(f"Response tidak valid: {data}")

            log.info(f"✅ tempmail.lol email dibuat: {self.email}")
            return {"email": self.email, "password": self.password}

        except Exception as e:
            log.error(f"❌ tempmail.lol create error: {e}")
            return {}

    def _get_messages(self) -> list:
        """Ambil daftar email dari inbox"""
        try:
            resp = requests.get(
                f"{TEMPMAIL_LOL_API}/auth/messages",
                params={"token": self._token},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            data = resp.json()
            return data.get("email", [])
        except Exception as e:
            log.debug(f"get_messages error: {e}")
            return []

    def find_otp_code(self, max_wait: int = 90) -> str:
        """Tunggu dan baca OTP dari inbox"""
        log.info(f"📬 Menunggu OTP di {self.email}...")
        elapsed  = 0
        interval = 5

        while elapsed < max_wait:
            messages = self._get_messages()
            for msg in messages:
                subject = msg.get("subject", "")
                body    = msg.get("body", "") or msg.get("html", "")
                log.info(f"📧 Email masuk: {subject}")
                otp = self._extract_otp(body)
                if otp:
                    return otp

            time.sleep(interval)
            elapsed += interval
            log.info(f"⏳ Menunggu OTP... ({elapsed}/{max_wait}s)")

        log.warning(f"⚠️ Timeout setelah {max_wait}s")
        return ""

    def find_verification_link(self, max_wait: int = 90) -> str:
        """Cari link verifikasi (fallback)"""
        elapsed  = 0
        interval = 5
        while elapsed < max_wait:
            messages = self._get_messages()
            for msg in messages:
                body = msg.get("body", "") or msg.get("html", "")
                for pat in [
                    r'https://zealy\.io/verify[^\s"<>]+',
                    r'https://[^\s"<>]*zealy[^\s"<>]*verify[^\s"<>]+',
                ]:
                    m = re.findall(pat, body, re.IGNORECASE)
                    if m:
                        log.info(f"✅ Link verifikasi: {m[0].rstrip('.')}")
                        return m[0].rstrip(".")
            time.sleep(interval)
            elapsed += interval
        return ""

    def _extract_otp(self, text: str) -> str:
        """Extract kode OTP 6 digit dari teks"""
        if not text:
            return ""
        patterns = [
            r'code[:\s]+(\d{6})',
            r'(\d{6})\s*is your',
            r'verification code[:\s]+(\d{6})',
            r'your code[:\s]+(\d{6})',
            r'enter[:\s]+(\d{6})',
            r'<[^>]*>\s*(\d{6})\s*<',
            r'\b(\d{6})\b',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                log.info(f"✅ OTP ditemukan: {matches[0]}")
                return matches[0]
        return ""

    def delete_account(self):
        """tempmail.lol tidak butuh delete — akun expired otomatis"""
        pass
