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
    Auto-generate email temporary dan baca inbox
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
        """Generate random string untuk username"""
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    def get_domains(self) -> list:
        """Ambil daftar domain aktif dari mail.tm"""
        try:
            response = self.session.get(f"{MAILTM_API}/domains")
            data = response.json()

            # Response bisa berupa list langsung atau dict dengan hydra:member
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

            # Jika kosong, coba fetch ulang domain yang valid
            log.warning("⚠️ Tidak ada domain dari API, mencoba fallback...")
            return self._get_fallback_domains()

        except Exception as e:
            log.error(f"❌ Gagal ambil domain mail.tm: {e}")
            return self._get_fallback_domains()

    def _get_fallback_domains(self) -> list:
        """Coba ambil domain valid secara manual"""
        try:
            # Coba endpoint alternatif
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
        # Fallback ke domain yang diketahui aktif
        return ["mailnull.com", "maildrop.cc"]

    def create_account(self) -> dict:
        """
        Auto-generate email baru di mail.tm
        Return: {"email": "...", "password": "..."}
        """
        domains = self.get_domains()
        domain = random.choice(domains)

        username = self._random_string(10)
        password = self._random_string(12) + "A1!"  # pastikan ada uppercase + digit + simbol

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

    def get_messages(self, max_wait: int = 60, interval: int = 5) -> list:
        """
        Tunggu dan ambil pesan masuk
        max_wait: maksimal waktu tunggu (detik)
        interval: cek setiap berapa detik
        """
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

            # Coba ambil text dulu, kalau tidak ada ambil HTML
            content = data.get("text", "") or data.get("html", [""])[0]
            return content

        except Exception as e:
            log.error(f"❌ Error ambil isi email: {e}")
            return ""

    def find_verification_link(self, max_wait: int = 60) -> str:
        """
        Cari link verifikasi dari email Zealy
        Return URL verifikasi atau string kosong jika tidak ditemukan
        """
        import re

        messages = self.get_messages(max_wait=max_wait)

        for msg in messages:
            msg_id = msg.get("id", "")
            subject = msg.get("subject", "")

            log.info(f"📧 Subject: {subject}")

            # Ambil isi email
            content = self.get_message_content(msg_id)

            if not content:
                continue

            # Cari link verifikasi Zealy
            # Pattern: https://zealy.io/verify/... atau https://zealy.io/api/...
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
