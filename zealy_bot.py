import requests
import random
import time
import logging
from config import (
    INVITE_LINK,
    COMMUNITY_SUBDOMAIN,
    ZEALY_API_BASE,
    DELAY_BETWEEN_REQUESTS,
    USER_AGENT,
)

log = logging.getLogger(__name__)


class ZealyBot:
    def __init__(self, email: str, password: str, twitter_username: str, proxy: str = None):
        self.email = email
        self.password = password
        self.twitter_username = twitter_username
        self.token = None
        self.user_id = None

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://zealy.io",
            "Referer": "https://zealy.io/",
        })

        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }
            log.info(f"[{self.email}] Menggunakan proxy: {proxy}")

    def _delay(self):
        """Delay random antara request"""
        delay = DELAY_BETWEEN_REQUESTS + random.uniform(0.5, 1.5)
        time.sleep(delay)

    def _set_auth_header(self):
        """Set header Authorization setelah login/register"""
        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })

    def register(self) -> bool:
        """Daftar akun baru di Zealy"""
        log.info(f"[{self.email}] Mencoba registrasi...")

        url = f"{ZEALY_API_BASE}/users"
        payload = {
            "email": self.email,
            "password": self.password,
            "name": self.twitter_username,
        }

        try:
            response = self.session.post(url, json=payload)
            data = response.json()

            if response.status_code in [200, 201]:
                self.token = data.get("token") or data.get("accessToken")
                self.user_id = data.get("id") or data.get("userId")
                log.info(f"[{self.email}] ✅ Registrasi berhasil! User ID: {self.user_id}")
                self._set_auth_header()
                return True
            elif response.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Email sudah terdaftar, mencoba login...")
                return self.login()
            else:
                log.error(f"[{self.email}] ❌ Registrasi gagal: {response.status_code} - {data}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error saat registrasi: {e}")
            return False

    def login(self) -> bool:
        """Login ke akun Zealy yang sudah ada"""
        log.info(f"[{self.email}] Mencoba login...")

        url = f"{ZEALY_API_BASE}/auth/login"
        payload = {
            "email": self.email,
            "password": self.password,
        }

        try:
            self._delay()
            response = self.session.post(url, json=payload)
            data = response.json()

            if response.status_code == 200:
                self.token = data.get("token") or data.get("accessToken")
                self.user_id = data.get("id") or data.get("userId")
                log.info(f"[{self.email}] ✅ Login berhasil! User ID: {self.user_id}")
                self._set_auth_header()
                return True
            else:
                log.error(f"[{self.email}] ❌ Login gagal: {response.status_code} - {data}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error saat login: {e}")
            return False

    def verify_email(self, verification_link: str) -> bool:
        """Klik link verifikasi email dari Zealy"""
        if not verification_link:
            log.warning(f"[{self.email}] ⚠️ Tidak ada link verifikasi")
            return False

        log.info(f"[{self.email}] Memverifikasi email via link...")

        try:
            self._delay()
            response = self.session.get(verification_link, allow_redirects=True)

            if response.status_code in [200, 201, 302]:
                log.info(f"[{self.email}] ✅ Email berhasil diverifikasi!")
                return True
            else:
                log.error(f"[{self.email}] ❌ Verifikasi gagal: {response.status_code}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error verifikasi email: {e}")
            return False

    def join_community_via_invite(self) -> bool:
        """Join komunitas Zealy via invite link"""
        log.info(f"[{self.email}] Mencoba join komunitas via invite link...")

        invite_code = INVITE_LINK.split("/invite/")[1].split("?")[0]
        quest_id = None
        if "questId=" in INVITE_LINK:
            quest_id = INVITE_LINK.split("questId=")[1]

        url = f"{ZEALY_API_BASE}/communities/{COMMUNITY_SUBDOMAIN}/members"
        payload = {"inviteCode": invite_code}
        if quest_id:
            payload["questId"] = quest_id

        try:
            self._delay()
            response = self.session.post(url, json=payload)
            data = response.json()

            if response.status_code in [200, 201]:
                log.info(f"[{self.email}] ✅ Berhasil join komunitas!")
                return True
            elif response.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Sudah join komunitas sebelumnya")
                return True
            else:
                log.error(f"[{self.email}] ❌ Gagal join komunitas: {response.status_code} - {data}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error saat join komunitas: {e}")
            return False

    def get_quests(self) -> list:
        """Ambil daftar quest yang tersedia"""
        log.info(f"[{self.email}] Mengambil daftar quest...")

        url = f"{ZEALY_API_BASE}/communities/{COMMUNITY_SUBDOMAIN}/quests"

        try:
            self._delay()
            response = self.session.get(url)
            data = response.json()

            if response.status_code == 200:
                quests = data if isinstance(data, list) else data.get("quests", [])
                log.info(f"[{self.email}] ✅ Ditemukan {len(quests)} quest")
                return quests
            else:
                log.error(f"[{self.email}] ❌ Gagal ambil quest: {response.status_code}")
                return []

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error saat ambil quest: {e}")
            return []

    def complete_quest(self, quest_id: str, quest_name: str = "") -> bool:
        """Coba complete sebuah quest"""
        log.info(f"[{self.email}] Mencoba complete quest: {quest_name or quest_id}")

        url = f"{ZEALY_API_BASE}/communities/{COMMUNITY_SUBDOMAIN}/quests/{quest_id}/claim"

        try:
            self._delay()
            response = self.session.post(url, json={})
            data = response.json()

            if response.status_code in [200, 201]:
                xp = data.get("xp", 0)
                log.info(f"[{self.email}] ✅ Quest '{quest_name}' selesai! +{xp} XP")
                return True
            elif response.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Quest sudah pernah di-complete")
                return True
            else:
                log.error(f"[{self.email}] ❌ Gagal complete quest: {response.status_code} - {data}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error saat complete quest: {e}")
            return False

    def complete_twitter_quest(self, quest_id: str, quest_name: str = "") -> bool:
        """Complete quest yang membutuhkan verifikasi Twitter"""
        log.info(f"[{self.email}] Mencoba complete Twitter quest: {quest_name or quest_id}")

        url = f"{ZEALY_API_BASE}/communities/{COMMUNITY_SUBDOMAIN}/quests/{quest_id}/claim"
        payload = {"twitterUsername": self.twitter_username}

        try:
            self._delay()
            response = self.session.post(url, json=payload)
            data = response.json()

            if response.status_code in [200, 201]:
                xp = data.get("xp", 0)
                log.info(f"[{self.email}] ✅ Twitter quest '{quest_name}' selesai! +{xp} XP")
                return True
            elif response.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Quest sudah pernah di-complete")
                return True
            else:
                log.error(f"[{self.email}] ❌ Gagal complete Twitter quest: {response.status_code} - {data}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error: {e}")
            return False

    def get_user_xp(self) -> int:
        """Cek XP user di komunitas"""
        url = f"{ZEALY_API_BASE}/communities/{COMMUNITY_SUBDOMAIN}/users/{self.user_id}"

        try:
            self._delay()
            response = self.session.get(url)
            data = response.json()

            if response.status_code == 200:
                xp = data.get("xp", 0)
                log.info(f"[{self.email}] 📊 XP saat ini: {xp}")
                return xp
            return 0

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error ambil XP: {e}")
            return 0

    def run(self, verification_link: str = "") -> dict:
        """Jalankan seluruh flow bot"""
        result = {
            "email": self.email,
            "twitter": self.twitter_username,
            "status": "failed",
            "xp": 0,
            "message": ""
        }

        # Step 1: Register
        if not self.register():
            result["message"] = "Gagal register/login"
            return result

        self._delay()

        # Step 2: Verifikasi email jika ada link
        if verification_link:
            self.verify_email(verification_link)
            self._delay()

        # Step 3: Join komunitas via invite link
        if not self.join_community_via_invite():
            result["message"] = "Gagal join komunitas"
            return result

        self._delay()

        # Step 4: Ambil dan complete quest
        quests = self.get_quests()
        completed_count = 0

        for quest in quests:
            quest_id = quest.get("id", "")
            quest_name = quest.get("name", quest.get("title", ""))
            quest_type = quest.get("type", "")

            # Skip quest yang butuh verifikasi manual
            skip_types = ["discord", "snapshot", "manual"]
            if any(t in quest_type.lower() for t in skip_types):
                log.info(f"[{self.email}] ⏭️ Skip quest manual: {quest_name}")
                continue

            # Complete Twitter quest vs quest biasa
            if "twitter" in quest_type.lower() or "x.com" in quest_name.lower():
                if self.complete_twitter_quest(quest_id, quest_name):
                    completed_count += 1
            else:
                if self.complete_quest(quest_id, quest_name):
                    completed_count += 1

            self._delay()

        # Step 5: Cek XP
        xp = self.get_user_xp()

        result["status"] = "success" if xp >= 1 else "partial"
        result["xp"] = xp
        result["message"] = f"Selesai! Complete {completed_count} quest, XP: {xp}"

        return result
