import re
import requests
import time
import random
import string
import logging

log = logging.getLogger(__name__)

MAILSLURP_API = "https://api.mailslurp.com"


class MailTM:
    """
    Email provider menggunakan MailSlurp API.
    Domain MailSlurp TIDAK di-blacklist Zealy.
    API key gratis: https://mailslurp.com (100 email/bulan gratis)
    """

    def __init__(self):
        from config import MAILSLURP_API_KEY
        self.api_key   = MAILSLURP_API_KEY
        self.email     = None
        self.password  = None
        self._inbox_id = None

        self._session = requests.Session()
        self._session.headers.update({
            "x-api-key":    self.api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        })

    def _random_string(self, length: int = 10) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    # ──────────────────────────────────────────
    #  CREATE INBOX
    # ──────────────────────────────────────────

    def create_account(self) -> dict:
        """Buat inbox baru via MailSlurp API"""
        try:
            resp = self._session.post(
                f"{MAILSLURP_API}/inboxes",
                json={
                    "name":        f"zealy-{self._random_string(6)}",
                    "expiresIn":   3600000,  # 1 jam dalam ms
                    "inboxType":   "HTTP_INBOX",
                }
            )
            data = resp.json()

            if resp.status_code not in [200, 201]:
                log.error(f"❌ MailSlurp error: {resp.status_code} - {data}")
                return {}

            self._inbox_id = data.get("id", "")
            self.email     = data.get("emailAddress", "")
            self.password  = self._random_string(12)

            if not self.email or not self._inbox_id:
                raise ValueError(f"Response tidak valid: {data}")

            log.info(f"✅ MailSlurp inbox dibuat: {self.email}")
            return {"email": self.email, "password": self.password}

        except Exception as e:
            log.error(f"❌ MailSlurp create error: {e}")
            return {}

    # ──────────────────────────────────────────
    #  READ INBOX
    # ──────────────────────────────────────────

    def _get_emails(self) -> list:
        """Ambil daftar email dari inbox"""
        try:
            resp = self._session.get(
                f"{MAILSLURP_API}/inboxes/{self._inbox_id}/emails",
                params={"sort": "DESC", "limit": 5}
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            log.debug(f"get_emails error: {e}")
            return []

    def _get_email_body(self, email_id: str) -> str:
        """Ambil isi lengkap sebuah email"""
        try:
            resp = self._session.get(f"{MAILSLURP_API}/emails/{email_id}")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("body", "") or data.get("html", "")
            return ""
        except Exception as e:
            log.debug(f"get_email_body error: {e}")
            return ""

    def find_otp_code(self, max_wait: int = 90) -> str:
        """Tunggu dan baca OTP dari inbox"""
        log.info(f"📬 Menunggu OTP di MailSlurp: {self.email}...")

        elapsed  = 0
        interval = 5

        while elapsed < max_wait:
            emails = self._get_emails()
            for em in emails:
                email_id = em.get("id", "")
                subject  = em.get("subject", "")
                log.info(f"📧 MailSlurp email masuk: {subject}")

                # Cek subject dulu (lebih cepat)
                otp = self._extract_otp(subject)
                if otp:
                    return otp

                # Ambil full body
                body = self._get_email_body(email_id)
                otp  = self._extract_otp(body)
                if otp:
                    return otp

            time.sleep(interval)
            elapsed += interval
            log.info(f"⏳ Menunggu OTP MailSlurp... ({elapsed}/{max_wait}s)")

        log.warning(f"⚠️ Timeout setelah {max_wait}s")
        return ""

    def find_verification_link(self, max_wait: int = 90) -> str:
        """Cari link verifikasi dari inbox (fallback)"""
        elapsed  = 0
        interval = 5

        while elapsed < max_wait:
            emails = self._get_emails()
            for em in emails:
                body = self._get_email_body(em.get("id", ""))
                for pat in [
                    r'https://zealy\.io/verify[^\s"<>]+',
                    r'https://[^\s"<>]*zealy[^\s"<>]*verify[^\s"<>]+',
                ]:
                    m = re.findall(pat, body, re.IGNORECASE)
                    if m:
                        link = m[0].rstrip(".")
                        log.info(f"✅ Link verifikasi: {link}")
                        return link
            time.sleep(interval)
            elapsed += interval

        return ""

    # ──────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────

    def _extract_otp(self, text: str) -> str:
        """
        Extract kode OTP dari teks.
        Zealy OTP format: 6 karakter alphanumeric (misal: Z3Ge9A)
        """
        if not text:
            return ""

        # Priority: Zealy OTP alphanumeric 6 karakter
        alphanum_patterns = [
            r'login code is\s+([A-Za-z0-9]{6})',           # "login code is Z3Ge9A"
            r'code is\s+([A-Za-z0-9]{6})',                  # "code is Z3Ge9A"
            r'code[:\s]+([A-Za-z0-9]{6})\b',               # "code: Z3Ge9A"
            r'([A-Za-z0-9]{6})\s+is your',                 # "Z3Ge9A is your code"
            r'verification code[:\s]+([A-Za-z0-9]{6})',    # "verification code: Z3Ge9A"
            r'your code[:\s]+([A-Za-z0-9]{6})',            # "your code: Z3Ge9A"
            r'enter[:\s]+([A-Za-z0-9]{6})',                # "enter: Z3Ge9A"
            r'<[^>]*>\s*([A-Za-z0-9]{6})\s*<',            # dalam HTML tag
        ]

        for pattern in alphanum_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                otp = matches[0]
                # Pastikan bukan kata umum
                if otp.lower() not in ['zealy', 'login', 'email', 'click', 'https']:
                    log.info(f"✅ OTP ditemukan: {otp}")
                    return otp

        # Fallback: cari 6 digit angka murni
        digit_patterns = [
            r'\b(\d{6})\b',
        ]
        for pattern in digit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                log.info(f"✅ OTP (numeric) ditemukan: {matches[0]}")
                return matches[0]

        return ""

    def delete_account(self):
        """Hapus inbox MailSlurp setelah selesai"""
        if not self._inbox_id:
            return
        try:
            self._session.delete(f"{MAILSLURP_API}/inboxes/{self._inbox_id}")
            log.info(f"🗑️ Inbox {self.email} dihapus")
        except Exception:
            pass
