import re
import requests
import random
import string
import time
import logging

log = logging.getLogger(__name__)

MAILTM_API      = "https://api.mail.tm"
GUERRILLA_API   = "https://api.guerrillamail.com/ajax.php"

# Domain Guerrilla Mail — tidak di-blacklist Zealy
GUERRILLA_DOMAINS = [
    "guerrillamailblock.com",
    "sharklasers.com",
    "guerrillamail.info",
    "grr.la",
    "guerrillamail.biz",
    "guerrillamail.de",
    "guerrillamail.net",
    "guerrillamail.org",
    "spam4.me",
]


class MailTM:
    """
    Wrapper untuk temp email.
    Primary: Guerrilla Mail (domain tidak di-blacklist Zealy)
    Fallback: mail.tm
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        # Guerrilla Mail state
        self._guerrilla_session_token = None
        self._guerrilla_sid_token     = None
        self._guerrilla_seq           = 0

        # mail.tm state
        self.token      = None
        self.account_id = None

        self.email    = None
        self.password = None
        self._mode    = None   # "guerrilla" atau "mailtm"

    def _random_string(self, length: int = 10) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    # ──────────────────────────────────────────
    #  GUERRILLA MAIL
    # ──────────────────────────────────────────

    def _guerrilla_create(self) -> dict:
        """Buat email baru via Guerrilla Mail API"""
        try:
            username = self._random_string(10)

            # Step 1: Init session dan dapat email random (JANGAN override domain)
            init_resp = requests.get(
                GUERRILLA_API,
                params={"f": "get_email_address", "lang": "en"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            init_data = init_resp.json()
            self._guerrilla_sid_token = init_data.get("sid_token", "")

            # Step 2: Set username custom (domain ikut default Guerrilla)
            resp = requests.get(
                GUERRILLA_API,
                params={
                    "f":           "set_email_user",
                    "email_user":  username,
                    "lang":        "en",
                    "sid_token":   self._guerrilla_sid_token,
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            data = resp.json()

            # Kalau set_email_user gagal, pakai email dari init saja
            email = data.get("email_addr") or init_data.get("email_addr", "")
            if not email:
                raise ValueError("Email addr kosong dari Guerrilla API")

            self._guerrilla_sid_token = data.get("sid_token") or self._guerrilla_sid_token
            self._guerrilla_seq       = data.get("email_timestamp", 0)

            self.email    = email
            self.password = self._random_string(12)
            self._mode    = "guerrilla"

            log.info(f"✅ Guerrilla email dibuat: {email}")
            return {"email": email, "password": self.password}

        except Exception as e:
            log.error(f"❌ Guerrilla Mail error: {e}")
            return {}

    def _guerrilla_get_messages(self) -> list:
        """Ambil pesan dari Guerrilla Mail"""
        try:
            resp = requests.get(
                GUERRILLA_API,
                params={
                    "f":         "check_email",
                    "seq":       self._guerrilla_seq,
                    "sid_token": self._guerrilla_sid_token,
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            data = resp.json()
            return data.get("list", [])
        except Exception as e:
            log.error(f"❌ Guerrilla check email error: {e}")
            return []

    def _guerrilla_get_message_body(self, mail_id: str) -> str:
        """Ambil isi email dari Guerrilla Mail"""
        try:
            resp = requests.get(
                GUERRILLA_API,
                params={
                    "f":         "fetch_email",
                    "email_id":  mail_id,
                    "sid_token": self._guerrilla_sid_token,
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            data = resp.json()
            return data.get("mail_body", "") or data.get("mail_excerpt", "")
        except Exception as e:
            log.error(f"❌ Guerrilla fetch email error: {e}")
            return ""

    def _guerrilla_wait_for_otp(self, max_wait: int = 90) -> str:
        """Tunggu OTP dari Guerrilla Mail"""
        log.info(f"📬 Menunggu OTP di Guerrilla inbox: {self.email}...")
        elapsed = 0
        interval = 5

        while elapsed < max_wait:
            messages = self._guerrilla_get_messages()
            for msg in messages:
                mail_id  = msg.get("mail_id", "")
                subject  = msg.get("mail_subject", "")
                excerpt  = msg.get("mail_excerpt", "")
                log.info(f"📧 Guerrilla email: {subject}")

                # Cek excerpt dulu (lebih cepat)
                otp = self._extract_otp(excerpt)
                if otp:
                    return otp

                # Ambil full body
                body = self._guerrilla_get_message_body(mail_id)
                otp = self._extract_otp(body)
                if otp:
                    return otp

            time.sleep(interval)
            elapsed += interval
            log.info(f"⏳ Menunggu email Guerrilla... ({elapsed}/{max_wait}s)")

        log.warning(f"⚠️ Timeout Guerrilla Mail setelah {max_wait}s")
        return ""

    # ──────────────────────────────────────────
    #  MAIL.TM (FALLBACK)
    # ──────────────────────────────────────────

    def _mailtm_get_domains(self) -> list:
        try:
            response = self.session.get(f"{MAILTM_API}/domains")
            data = response.json()
            if isinstance(data, list):
                return [d["domain"] for d in data if "domain" in d]
            return [d["domain"] for d in data.get("hydra:member", []) if "domain" in d]
        except Exception:
            return ["mailnull.com"]

    def _mailtm_create(self) -> dict:
        """Buat email baru via mail.tm (fallback)"""
        domains  = self._mailtm_get_domains()
        domain   = random.choice(domains)
        username = self._random_string(10)
        password = self._random_string(12) + "A1!"
        email    = f"{username}@{domain}"

        try:
            response = self.session.post(
                f"{MAILTM_API}/accounts",
                json={"address": email, "password": password}
            )
            data = response.json()
            if response.status_code in [200, 201]:
                self.email       = email
                self.password    = password
                self.account_id  = data.get("id")
                self._mode       = "mailtm"
                self._mailtm_login()
                log.info(f"✅ mail.tm email dibuat: {email}")
                return {"email": email, "password": password}
            else:
                log.error(f"❌ mail.tm error: {response.status_code} - {data}")
                return {}
        except Exception as e:
            log.error(f"❌ mail.tm create error: {e}")
            return {}

    def _mailtm_login(self) -> bool:
        try:
            response = self.session.post(
                f"{MAILTM_API}/token",
                json={"address": self.email, "password": self.password}
            )
            data = response.json()
            if response.status_code == 200:
                self.token = data.get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
            return False
        except Exception:
            return False

    def _mailtm_get_messages(self, max_wait: int = 90) -> list:
        log.info(f"📬 Menunggu OTP di mail.tm inbox: {self.email}...")
        elapsed = 0
        interval = 5

        while elapsed < max_wait:
            try:
                response = self.session.get(f"{MAILTM_API}/messages")
                data = response.json()
                messages = data.get("hydra:member", [])
                if messages:
                    return messages
                time.sleep(interval)
                elapsed += interval
                log.info(f"⏳ Menunggu email mail.tm... ({elapsed}/{max_wait}s)")
            except Exception as e:
                log.error(f"❌ mail.tm check error: {e}")
                time.sleep(interval)
                elapsed += interval
        return []

    def _mailtm_get_body(self, message_id: str) -> str:
        try:
            response = self.session.get(f"{MAILTM_API}/messages/{message_id}")
            data = response.json()
            content = data.get("text", "")
            if not content:
                html_list = data.get("html", [])
                content = html_list[0] if html_list else ""
            return content
        except Exception:
            return ""

    def _mailtm_wait_for_otp(self, max_wait: int = 90) -> str:
        messages = self._mailtm_get_messages(max_wait=max_wait)
        for msg in messages:
            msg_id  = msg.get("id", "")
            subject = msg.get("subject", "")
            log.info(f"📧 mail.tm email: {subject}")
            body = self._mailtm_get_body(msg_id)
            otp = self._extract_otp(body)
            if otp:
                return otp
        return ""

    # ──────────────────────────────────────────
    #  SHARED HELPERS
    # ──────────────────────────────────────────

    def _extract_otp(self, text: str) -> str:
        """Extract kode OTP 6 digit dari teks"""
        if not text:
            return ""

        otp_patterns = [
            r'code[:\s]+(\d{6})',
            r'(\d{6})\s*is your',
            r'verification code[:\s]+(\d{6})',
            r'your code[:\s]+(\d{6})',
            r'enter[:\s]+(\d{6})',
            r'<[^>]*>(\d{6})<',
            r'\b(\d{6})\b',
        ]

        for pattern in otp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                otp = matches[0]
                log.info(f"✅ OTP ditemukan: {otp}")
                return otp
        return ""

    # ──────────────────────────────────────────
    #  PUBLIC API
    # ──────────────────────────────────────────

    def create_account(self) -> dict:
        """
        Buat email temporary.
        Coba Guerrilla Mail dulu (domain tidak di-blacklist Zealy),
        fallback ke mail.tm jika gagal.
        """
        # Coba Guerrilla Mail
        result = self._guerrilla_create()
        if result:
            return result

        # Fallback ke mail.tm
        log.warning("⚠️ Guerrilla Mail gagal, fallback ke mail.tm...")
        return self._mailtm_create()

    def find_otp_code(self, max_wait: int = 90) -> str:
        """Tunggu dan ambil OTP dari inbox"""
        if self._mode == "guerrilla":
            return self._guerrilla_wait_for_otp(max_wait=max_wait)
        else:
            return self._mailtm_wait_for_otp(max_wait=max_wait)

    def find_verification_link(self, max_wait: int = 90) -> str:
        """Cari link verifikasi dari inbox (fallback)"""
        if self._mode == "guerrilla":
            messages = self._guerrilla_get_messages()
            bodies = [self._guerrilla_get_message_body(m.get("mail_id", "")) for m in messages]
        else:
            msgs = self._mailtm_get_messages(max_wait=max_wait)
            bodies = [self._mailtm_get_body(m.get("id", "")) for m in msgs]

        patterns = [
            r'https://zealy\.io/verify[^\s"<>]+',
            r'https://[^\s"<>]*zealy[^\s"<>]*verify[^\s"<>]+',
            r'https://[^\s"<>]*zealy[^\s"<>]*confirm[^\s"<>]+',
        ]
        for body in bodies:
            for pattern in patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    link = matches[0].rstrip('.')
                    log.info(f"✅ Link verifikasi: {link}")
                    return link
        return ""

    def delete_account(self):
        """Hapus akun mail.tm (Guerrilla tidak butuh delete)"""
        if self._mode == "mailtm" and self.account_id:
            try:
                self.session.delete(f"{MAILTM_API}/accounts/{self.account_id}")
                log.info(f"🗑️ Akun mail.tm {self.email} dihapus")
            except Exception:
                pass
