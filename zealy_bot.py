import requests
import random
import time
import logging
from config import (
    INVITE_LINK,
    COMMUNITY_SUBDOMAIN,
    DELAY_BETWEEN_REQUESTS,
    USER_AGENT,
)

log = logging.getLogger(__name__)

# Zealy API endpoints
ZEALY_API      = "https://api-v2.zealy.io/public"
ZEALY_BACKEND  = "https://backend.zealy.io"
ZEALY_API_V1   = "https://api-v1.zealy.io"


class ZealyBot:
    """
    Bot Zealy dengan flow OTP (passwordless email auth).

    Flow:
      1. send_otp(email)       → Zealy kirim OTP ke inbox
      2. verify_otp(email,otp) → dapat access_token
      3. create_profile(name)  → set username pertama kali
      4. join_community()      → join via invite link
      5. complete_quests()     → complete semua quest otomatis
    """

    def __init__(self, email: str, twitter_username: str, proxy: str = None):
        self.email = email
        self.twitter_username = twitter_username
        self.token = None
        self.user_id = None

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://zealy.io",
            "Referer": "https://zealy.io/sign-up",
        })

        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
            log.info(f"[{self.email}] Menggunakan proxy: {proxy}")

    # ─────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────

    def _delay(self, extra: float = 0):
        time.sleep(DELAY_BETWEEN_REQUESTS + random.uniform(0.5, 1.5) + extra)

    def _set_auth(self):
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _log_response(self, label: str, resp):
        log.debug(f"[{self.email}] {label} → {resp.status_code}: {resp.text[:200]}")

    # ─────────────────────────────────────────────
    #  STEP 1: Kirim OTP ke email
    # ─────────────────────────────────────────────

    def send_otp(self) -> bool:
        """
        Kirim OTP ke email via Zealy.
        Endpoint yang benar: POST /otp/send  (dari source JS Zealy)
        """
        log.info(f"[{self.email}] 📨 Mengirim OTP ke email...")

        # Endpoint yang ditemukan dari source JS Zealy:
        # path:"/otp/send"  body:{email}
        endpoints_to_try = [
            (f"{ZEALY_API_V1}/otp/send",  {"email": self.email}),
            (f"{ZEALY_API}/otp/send",     {"email": self.email}),
            (f"{ZEALY_BACKEND}/otp/send", {"email": self.email}),
        ]

        for url, payload in endpoints_to_try:
            try:
                response = self.session.post(url, json=payload)
                self._log_response(f"send_otp {url}", response)

                if response.status_code in [200, 201, 202]:
                    log.info(f"[{self.email}] ✅ OTP terkirim via {url}")
                    return True

                if response.status_code == 400:
                    try:
                        err = response.json()
                    except Exception:
                        err = response.text
                    log.warning(f"[{self.email}] ⚠️ 400 di {url}: {str(err)[:150]}")
                    # 400 berarti endpoint ada — kemungkinan email format/rate limit
                    # Lanjut coba endpoint berikutnya saja
                    continue

                if response.status_code in [404, 405]:
                    continue

            except Exception as e:
                log.error(f"[{self.email}] ❌ Error send_otp {url}: {e}")
                continue

        log.error(f"[{self.email}] ❌ Semua endpoint send_otp gagal")
        return False

    # ─────────────────────────────────────────────
    #  STEP 2: Verifikasi OTP
    # ─────────────────────────────────────────────

    def verify_otp(self, otp: str) -> bool:
        """
        Submit OTP code dan dapatkan token.
        Endpoint yang benar: POST /otp/verify  body:{email, otp}  (dari source JS Zealy)
        """
        log.info(f"[{self.email}] 🔑 Memverifikasi OTP: {otp}")

        endpoints_to_try = [
            (f"{ZEALY_API_V1}/otp/verify", {"email": self.email, "otp": otp}),
            (f"{ZEALY_API}/otp/verify",    {"email": self.email, "otp": otp}),
            (f"{ZEALY_BACKEND}/otp/verify",{"email": self.email, "otp": otp}),
        ]

        for url, payload in endpoints_to_try:
            try:
                self._delay()
                response = self.session.post(url, json=payload)
                self._log_response(f"verify_otp {url}", response)

                if response.status_code in [200, 201]:
                    data = response.json()
                    self.token = (
                        data.get("accessToken") or
                        data.get("access_token") or
                        data.get("token") or
                        data.get("jwt")
                    )
                    self.user_id = (
                        data.get("id") or
                        data.get("userId") or
                        data.get("user", {}).get("id")
                    )

                    if self.token:
                        log.info(f"[{self.email}] ✅ OTP verified! User ID: {self.user_id}")
                        self._set_auth()
                        return True
                    else:
                        log.warning(f"[{self.email}] ⚠️ Response 200 tapi tidak ada token: {str(data)[:150]}")

                if response.status_code in [404, 405]:
                    continue

            except Exception as e:
                log.error(f"[{self.email}] ❌ Error verify_otp {url}: {e}")
                continue

        log.error(f"[{self.email}] ❌ Semua endpoint verify_otp gagal")
        return False

    # ─────────────────────────────────────────────
    #  STEP 3: Set username (create profile)
    # ─────────────────────────────────────────────

    def create_profile(self) -> bool:
        """Set username / nama akun setelah registrasi pertama kali"""
        log.info(f"[{self.email}] 👤 Membuat profil dengan username: {self.twitter_username}")

        # Generate username yang unik (tambah angka random di belakang)
        username = f"{self.twitter_username}{random.randint(100, 999)}"

        url = f"{ZEALY_BACKEND}/users/me"
        payload = {
            "name": username,
            "username": username,
        }

        try:
            self._delay()
            response = self.session.patch(url, json=payload)
            self._log_response("create_profile", response)

            if response.status_code in [200, 201]:
                data = response.json()
                self.user_id = self.user_id or data.get("id")
                log.info(f"[{self.email}] ✅ Profil dibuat: {username}")
                return True
            elif response.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Username sudah dipakai, coba lagi...")
                payload["username"] = f"{self.twitter_username}{random.randint(1000, 9999)}"
                self._delay()
                r2 = self.session.patch(url, json=payload)
                if r2.status_code in [200, 201]:
                    log.info(f"[{self.email}] ✅ Profil dibuat (retry)")
                    return True
            else:
                log.warning(f"[{self.email}] ⚠️ Profil gagal dibuat: {response.status_code} — lanjut saja")
                return True  # Tidak kritis, lanjut

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error create_profile: {e}")

        return True  # Non-blocking

    # ─────────────────────────────────────────────
    #  STEP 4: Join komunitas via invite link
    # ─────────────────────────────────────────────

    def join_community(self) -> bool:
        """Join komunitas Zealy via invite link"""
        log.info(f"[{self.email}] 🔗 Mencoba join komunitas...")

        invite_code = INVITE_LINK.split("/invite/")[1].split("?")[0]
        quest_id = INVITE_LINK.split("questId=")[1] if "questId=" in INVITE_LINK else None

        payload = {"inviteCode": invite_code}
        if quest_id:
            payload["questId"] = quest_id

        endpoints_to_try = [
            f"{ZEALY_API}/communities/{COMMUNITY_SUBDOMAIN}/members",
            f"{ZEALY_BACKEND}/public/communities/{COMMUNITY_SUBDOMAIN}/members",
        ]

        for url in endpoints_to_try:
            try:
                self._delay()
                response = self.session.post(url, json=payload)
                self._log_response(f"join_community {url}", response)

                if response.status_code in [200, 201]:
                    log.info(f"[{self.email}] ✅ Berhasil join komunitas!")
                    return True
                elif response.status_code == 409:
                    log.warning(f"[{self.email}] ⚠️ Sudah join komunitas sebelumnya")
                    return True
                elif response.status_code == 404:
                    continue

            except Exception as e:
                log.error(f"[{self.email}] ❌ Error join_community: {e}")
                continue

        log.error(f"[{self.email}] ❌ Gagal join komunitas")
        return False

    # ─────────────────────────────────────────────
    #  STEP 5: Ambil dan complete quest
    # ─────────────────────────────────────────────

    def get_quests(self) -> list:
        """Ambil daftar quest yang tersedia"""
        log.info(f"[{self.email}] 📋 Mengambil daftar quest...")

        urls = [
            f"{ZEALY_API}/communities/{COMMUNITY_SUBDOMAIN}/quests",
            f"{ZEALY_BACKEND}/public/communities/{COMMUNITY_SUBDOMAIN}/quests",
        ]

        for url in urls:
            try:
                self._delay()
                response = self.session.get(url)

                if response.status_code == 200:
                    data = response.json()
                    quests = data if isinstance(data, list) else data.get("quests", [])
                    log.info(f"[{self.email}] ✅ Ditemukan {len(quests)} quest")
                    return quests
                elif response.status_code == 404:
                    continue

            except Exception as e:
                log.error(f"[{self.email}] ❌ Error get_quests: {e}")
                continue

        return []

    def claim_quest(self, quest_id: str, quest_name: str = "", is_twitter: bool = False) -> bool:
        """Claim sebuah quest"""
        log.info(f"[{self.email}] 🎯 Claiming quest: {quest_name or quest_id}")

        url = f"{ZEALY_API}/communities/{COMMUNITY_SUBDOMAIN}/quests/{quest_id}/claim"
        payload = {"twitterUsername": self.twitter_username} if is_twitter else {}

        try:
            self._delay()
            response = self.session.post(url, json=payload)
            self._log_response(f"claim_quest {quest_name}", response)

            if response.status_code in [200, 201]:
                xp = response.json().get("xp", 0)
                log.info(f"[{self.email}] ✅ Quest '{quest_name}' berhasil! +{xp} XP")
                return True
            elif response.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Quest '{quest_name}' sudah pernah di-claim")
                return True
            else:
                log.warning(f"[{self.email}] ⚠️ Quest '{quest_name}' gagal: {response.status_code}")
                return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error claim_quest: {e}")
            return False

    def complete_quests(self) -> int:
        """Ambil dan complete semua quest yang bisa di-automate"""
        quests = self.get_quests()
        completed = 0

        SKIP_TYPES = ["discord", "snapshot", "manual", "wallet", "nft", "token"]

        for quest in quests:
            quest_id   = quest.get("id", "")
            quest_name = quest.get("name", quest.get("title", ""))
            quest_type = quest.get("type", "").lower()

            if not quest_id:
                continue

            # Skip quest yang butuh verifikasi manual/external
            if any(t in quest_type for t in SKIP_TYPES):
                log.info(f"[{self.email}] ⏭️ Skip quest ({quest_type}): {quest_name}")
                continue

            is_twitter = "twitter" in quest_type or "x.com" in quest_name.lower()
            if self.claim_quest(quest_id, quest_name, is_twitter=is_twitter):
                completed += 1

            self._delay()

        return completed

    def get_user_xp(self) -> int:
        """Cek XP user saat ini"""
        if not self.user_id:
            return 0

        urls = [
            f"{ZEALY_API}/communities/{COMMUNITY_SUBDOMAIN}/users/{self.user_id}",
            f"{ZEALY_BACKEND}/public/communities/{COMMUNITY_SUBDOMAIN}/users/{self.user_id}",
        ]

        for url in urls:
            try:
                self._delay()
                response = self.session.get(url)
                if response.status_code == 200:
                    xp = response.json().get("xp", 0)
                    log.info(f"[{self.email}] 📊 XP: {xp}")
                    return xp
            except Exception:
                continue

        return 0

    # ─────────────────────────────────────────────
    #  MAIN RUN — dipanggil dari main.py setelah OTP dikirim
    # ─────────────────────────────────────────────

    def run_after_otp(self, otp: str) -> dict:
        """
        Jalankan flow setelah OTP didapat dari inbox.
        Dipanggil dari main.py setelah mail_tm.find_otp_code() berhasil.
        """
        result = {
            "email": self.email,
            "twitter": self.twitter_username,
            "status": "failed",
            "xp": 0,
            "message": ""
        }

        # Step 2: Verify OTP
        if not self.verify_otp(otp):
            result["message"] = "OTP tidak valid atau endpoint tidak ditemukan"
            return result

        self._delay()

        # Step 3: Buat profil
        self.create_profile()
        self._delay()

        # Step 4: Join komunitas
        if not self.join_community():
            result["message"] = "Gagal join komunitas"
            return result

        self._delay()

        # Step 5: Complete quests
        completed = self.complete_quests()

        # Step 6: Cek XP
        xp = self.get_user_xp()

        result["status"] = "success" if xp >= 1 else "partial"
        result["xp"] = xp
        result["message"] = f"Selesai! {completed} quest di-claim, XP: {xp}"

        return result
