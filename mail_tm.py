import re
import requests
import random
import string
import time
import logging

log = logging.getLogger(__name__)

MAILTM_API = "https://api.mail.tm"


class MailTM:
    """
    Wrapper untuk mail.tm API
    Auto-generate email temporary, baca inbox, dan extract OTP/link
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.email = None
        self.password = None
        self.token = None
        self.account_id = None

    def _random_string(self, length: int = 10) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    def get_domains(self) -> list:
        """Ambil daftar domain aktif dari mail.tm"""
        try:
            response = self.session.get(f"{MAILTM_API}/domains")
            data = response.json()

            if isinstance(data, list):
                domains = [d["domain"] for d in data if "domain" in d]
            elif isinstance(data, dict):
                members = data.get("hydra:member", [])
                domains = [d["domain"] for d in members if "domain" in d]
            else:
                domains = []

            if domains:
                log.info(f"✅ Domain tersedia: {domains}")
                return domains

            log.warning("⚠️ Tidak ada domain dari API, mencoba fallback...")
            return self._get_fallback_domains()

        except Exception as e:
            log.error(f"❌ Gagal ambil domain mail.tm: {e}")
            return self._get_fallback_domains()

    def _get_fallback_domains(self) -> list:
        try:
            response = self.session.get(f"{MAILTM_API}/domains?page=1")
            data = response.json()
            if isinstance(data, list):
                domains = [d["domain"] for d in data if "domain" in d]
            else:
                domains = [d["domain"] for d in data.get("hydra:member", []) if "domain" in d]
            if domains:
                return domains
        except Exception:
            pass
        return ["mailnull.com", "maildrop.cc"]

    def get_all_domains(self) -> list:
        """Ambil semua domain yang tersedia dari semua page"""
        all_domains = []
        try:
            for page in range(1, 4):
                response = self.session.get(f"{MAILTM_API}/domains?page={page}")
                if response.status_code != 200:
                    break
                data = response.json()
                if isinstance(data, list):
                    domains = [d["domain"] for d in data if "domain" in d]
                else:
                    domains = [d["domain"] for d in data.get("hydra:member", []) if "domain" in d]
                if not domains:
                    break
                all_domains.extend(domains)
        except Exception:
            pass
        return all_domains if all_domains else self._get_fallback_domains()

    def create_account(self) -> dict:
        """Auto-generate email baru di mail.tm"""
        domains = self.get_domains()
        domain = random.choice(domains)
        username = self._random_string(10)
        password = self._random_string(12) + "A1!"
        email = f"{username}@{domain}"

        try:
            response = self.session.post(
                f"{MAILTM_API}/accounts",
                json={"address": email, "password": password}
            )
            data = response.json()

            if response.status_code in [200, 201]:
                self.email = email
                self.password = password
                self.account_id = data.get("id")
                log.info(f"✅ Email temp berhasil dibuat: {email}")
                self._login()
                return {"email": email, "password": password}
            else:
                log.error(f"❌ Gagal buat email: {response.status_code} - {data}")
                return {}

        except Exception as e:
            log.error(f"❌ Error buat email: {e}")
            return {}

    def _login(self) -> bool:
        """Login ke mail.tm untuk ambil token"""
        try:
            response = self.session.post(
                f"{MAILTM_API}/token",
                json={"address": self.email, "password": self.password}
            )
            data = response.json()

            if response.status_code == 200:
                self.token = data.get("token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                return True
            else:
                log.error(f"❌ Login mail.tm gagal: {data}")
                return False

        except Exception as e:
            log.error(f"❌ Error login mail.tm: {e}")
            return False

    def get_messages(self, max_wait: int = 90, interval: int = 5) -> list:
        """Tunggu dan ambil pesan masuk"""
        log.info(f"📬 Menunggu email masuk di {self.email}...")
        elapsed = 0

        while elapsed < max_wait:
            try:
                response = self.session.get(f"{MAILTM_API}/messages")
                data = response.json()
                messages = data.get("hydra:member", [])

                if messages:
                    log.info(f"✅ Ada {len(messages)} email masuk!")
                    return messages

                time.sleep(interval)
                elapsed += interval
                log.info(f"⏳ Menunggu email... ({elapsed}/{max_wait}s)")

            except Exception as e:
                log.error(f"❌ Error cek inbox: {e}")
                time.sleep(interval)
                elapsed += interval

        log.warning(f"⚠️ Timeout menunggu email setelah {max_wait} detik")
        return []

    def get_message_content(self, message_id: str) -> str:
        """Ambil isi lengkap sebuah email"""
        try:
            response = self.session.get(f"{MAILTM_API}/messages/{message_id}")
            data = response.json()
            # Coba text dulu, fallback ke HTML
            content = data.get("text", "")
            if not content:
                html_list = data.get("html", [])
                content = html_list[0] if html_list else ""
            return content

        except Exception as e:
            log.error(f"❌ Error ambil isi email: {e}")
            return ""

    def find_otp_code(self, max_wait: int = 90) -> str:
        """
        Tunggu email dari Zealy dan extract kode OTP 6 digit.
        Return: string kode OTP atau '' jika tidak ditemukan
        """
        messages = self.get_messages(max_wait=max_wait)

        for msg in messages:
            msg_id = msg.get("id", "")
            subject = msg.get("subject", "")
            log.info(f"📧 Subject email: {subject}")

            content = self.get_message_content(msg_id)
            if not content:
                continue

            # Pattern OTP: 6 angka yang berdiri sendiri
            otp_patterns = [
                r'\b(\d{6})\b',                          # 6 digit angka
                r'code[:\s]+(\d{6})',                    # "code: 123456"
                r'(\d{6})\s*is your',                    # "123456 is your code"
                r'verification code[:\s]+(\d{6})',       # "verification code: 123456"
                r'your code[:\s]+(\d{6})',               # "your code: 123456"
                r'enter[:\s]+(\d{6})',                   # "enter: 123456"
                r'<[^>]*>(\d{6})<',                      # OTP di dalam HTML tag
            ]

            for pattern in otp_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    otp = matches[0]
                    log.info(f"✅ OTP ditemukan: {otp}")
                    return otp

            # Fallback: cari semua 6 digit, ambil yang paling cocok
            all_digits = re.findall(r'\b\d{6}\b', content)
            if all_digits:
                otp = all_digits[0]
                log.info(f"✅ OTP ditemukan (fallback): {otp}")
                return otp

            log.warning(f"⚠️ Tidak ada OTP di email: {subject}")

        return ""

    def find_verification_link(self, max_wait: int = 90) -> str:
        """
        Cari link verifikasi dari email Zealy (fallback jika pakai link bukan OTP)
        """
        messages = self.get_messages(max_wait=max_wait)

        for msg in messages:
            msg_id = msg.get("id", "")
            subject = msg.get("subject", "")
            log.info(f"📧 Subject: {subject}")

            content = self.get_message_content(msg_id)
            if not content:
                continue

            patterns = [
                r'https://zealy\.io/verify[^\s"<>]+',
                r'https://zealy\.io/api/auth/verify[^\s"<>]+',
                r'https://api\.zealy\.io/users/verify[^\s"<>]+',
                r'https://[^\s"<>]*zealy[^\s"<>]*verify[^\s"<>]+',
                r'https://[^\s"<>]*zealy[^\s"<>]*confirm[^\s"<>]+',
                r'https://[^\s"<>]*zealy[^\s"<>]*token=[^\s"<>]+',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    link = matches[0].rstrip('.')
                    log.info(f"✅ Link verifikasi ditemukan: {link}")
                    return link

            log.warning(f"⚠️ Tidak ada link verifikasi di email: {subject}")

        return ""

    def delete_account(self):
        """Hapus akun mail.tm setelah selesai"""
        if not self.account_id:
            return
        try:
            self.session.delete(f"{MAILTM_API}/accounts/{self.account_id}")
            log.info(f"🗑️ Akun email {self.email} dihapus")
        except Exception as e:
            log.error(f"❌ Error hapus akun email: {e}")
