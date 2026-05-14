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
from captcha_solver import CaptchaSolver

log = logging.getLogger(__name__)

# Zealy API endpoints (dari reverse engineering JS source)
ZEALY_V1  = "https://api-v1.zealy.io"
ZEALY_V2  = "https://api-v2.zealy.io"


class ZealyBot:
    """
    Zealy bot — flow:
      1. solve_turnstile()      → dapat token captcha via 2captcha
      2. send_otp()             → kirim OTP ke email
      3. verify_otp(otp)        → verify OTP → dapat JWT token
      4. create_profile()       → set username
      5. join_community()       → join via invite link
      6. complete_quests()      → auto-claim quest
    """

    def __init__(self, email: str, twitter_username: str, proxy: str = None):
        self.email = email
        self.twitter_username = twitter_username
        self.token = None
        self.user_id = None
        self.captcha = CaptchaSolver()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent":   USER_AGENT,
            "Content-Type": "application/json",
            "Accept":       "application/json",
            "Origin":       "https://zealy.io",
            "Referer":      "https://zealy.io/sign-up",
        })

        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
            log.info(f"[{self.email}] Proxy: {proxy}")

    # ─────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────

    def _delay(self, extra: float = 0):
        time.sleep(DELAY_BETWEEN_REQUESTS + random.uniform(0.5, 1.5) + extra)

    def _set_auth(self):
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _post(self, url: str, payload: dict) -> requests.Response:
        """Wrapper POST dengan logging"""
        resp = self.session.post(url, json=payload)
        log.debug(f"[{self.email}] POST {url} → {resp.status_code}: {resp.text[:200]}")
        return resp

    def _get(self, url: str) -> requests.Response:
        resp = self.session.get(url)
        log.debug(f"[{self.email}] GET  {url} → {resp.status_code}: {resp.text[:200]}")
        return resp

    # ─────────────────────────────────────────────
    #  STEP 1: Solve Turnstile
    # ─────────────────────────────────────────────

    def solve_turnstile(self) -> str:
        """Solve Cloudflare Turnstile via 2captcha. Return token."""
        log.info(f"[{self.email}] 🔐 Solving Turnstile via 2captcha...")
        token = self.captcha.solve_turnstile()
        if not token:
            log.error(f"[{self.email}] ❌ Gagal solve Turnstile")
        return token

    # ─────────────────────────────────────────────
    #  STEP 2: Kirim OTP
    # ─────────────────────────────────────────────

    def send_otp(self, turnstile_token: str) -> bool:
        """
        Kirim OTP ke email.
        Endpoint: POST /api/authentication/otp/send  (api-v2.zealy.io)
        Body: { email, turnstileToken }
        """
        log.info(f"[{self.email}] 📨 Mengirim OTP...")

        url = f"{ZEALY_V2}/api/authentication/otp/send"
        payload = {
            "email":          self.email,
            "turnstileToken": turnstile_token,
        }

        try:
            resp = self._post(url, payload)

            if resp.status_code in [200, 201, 202]:
                log.info(f"[{self.email}] ✅ OTP terkirim ke {self.email}")
                return True

            log.error(f"[{self.email}] ❌ send_otp gagal: {resp.status_code} — {resp.text[:200]}")
            return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error send_otp: {e}")
            return False

    # ─────────────────────────────────────────────
    #  STEP 3: Verify OTP → dapat JWT token
    # ─────────────────────────────────────────────

    def verify_otp(self, otp: str, turnstile_token: str) -> bool:
        """
        Verify OTP dan dapat JWT token.
        Endpoint: POST /api/authentication/otp/verify  (api-v2.zealy.io)
        Body: { email, otp }
        Note: Zealy OTP = 6 karakter alphanumeric (misal: Z3Ge9A), bukan 6 digit
        Note: Jangan delay sebelum verify — OTP cepat expire!
        """
        log.info(f"[{self.email}] 🔑 Verifying OTP: {otp}")

        url = f"{ZEALY_V2}/api/authentication/otp/verify"
        # Kirim OTP apa adanya (alphanumeric 6 karakter)
        # Sertakan turnstileToken juga untuk jaga-jaga
        payload = {
            "email": self.email,
            "otp": otp,
            "turnstileToken": turnstile_token,
        }

        try:
            # TIDAK delay sebelum verify — OTP Zealy expire cepat!
            # Only strip +alias for Gmail addresses
            # For other providers (MailSlurp etc), use email as-is
            if "gmail.com" in self.email and "+" in self.email:
                base_email = self.email.split("+")[0] + "@" + self.email.split("@")[1]
                log.info(f"[{self.email}] 🔄 Verify dengan base email: {base_email}")
                payload["email"] = base_email

            resp = self._post(url, payload)

            if resp.status_code in [200, 201]:
                data = resp.json()
                log.info(f"[{self.email}] 🔍 verify_otp response: {str(data)[:300]}")
                # Zealy return token dalam berbagai field
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
                    log.warning(f"[{self.email}] ⚠️ 200 OK tapi tidak ada token: {str(data)[:150]}")
                    return False

            log.error(f"[{self.email}] ❌ verify_otp gagal: {resp.status_code} — {resp.text[:200]}")
            return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error verify_otp: {e}")
            return False

    # ─────────────────────────────────────────────
    #  STEP 4: Create profile
    # ─────────────────────────────────────────────

    def create_profile(self) -> bool:
        """Set username setelah pertama kali login"""
        username = f"{self.twitter_username}{random.randint(100, 999)}"
        log.info(f"[{self.email}] 👤 Set username: {username}")

        url = f"{ZEALY_V1}/users/me"
        payload = {"name": username, "username": username}

        try:
            self._delay()
            resp = self.session.patch(url, json=payload)

            if resp.status_code in [200, 201]:
                data = resp.json()
                self.user_id = self.user_id or data.get("id")
                log.info(f"[{self.email}] ✅ Profile dibuat: {username}")
                return True

            if resp.status_code == 409:
                # Username taken, coba lagi
                payload["username"] = f"{self.twitter_username}{random.randint(1000, 9999)}"
                self._delay()
                resp2 = self.session.patch(url, json=payload)
                if resp2.status_code in [200, 201]:
                    log.info(f"[{self.email}] ✅ Profile dibuat (retry)")
                    return True

            log.warning(f"[{self.email}] ⚠️ Profile gagal ({resp.status_code}) — lanjut")
            return True   # non-blocking

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error create_profile: {e}")
            return True   # non-blocking

    # ─────────────────────────────────────────────
    #  STEP 5: Join komunitas
    # ─────────────────────────────────────────────

    def join_community(self) -> bool:
        """Join komunitas Zealy via invite link"""
        log.info(f"[{self.email}] 🔗 Join komunitas...")

        invite_code = INVITE_LINK.split("/invite/")[1].split("?")[0]
        quest_id    = INVITE_LINK.split("questId=")[1] if "questId=" in INVITE_LINK else None

        payload = {"inviteCode": invite_code}
        if quest_id:
            payload["questId"] = quest_id

        urls = [
            f"{ZEALY_V2}/public/communities/{COMMUNITY_SUBDOMAIN}/members",
            f"{ZEALY_V1}/communities/{COMMUNITY_SUBDOMAIN}/members",
        ]

        for url in urls:
            try:
                self._delay()
                resp = self._post(url, payload)

                if resp.status_code in [200, 201]:
                    log.info(f"[{self.email}] ✅ Joined komunitas!")
                    return True
                if resp.status_code == 409:
                    log.warning(f"[{self.email}] ⚠️ Sudah join sebelumnya")
                    return True
                if resp.status_code == 404:
                    continue

            except Exception as e:
                log.error(f"[{self.email}] ❌ Error join: {e}")
                continue

        log.error(f"[{self.email}] ❌ Gagal join komunitas")
        return False

    # ─────────────────────────────────────────────
    #  STEP 6: Complete quests
    # ─────────────────────────────────────────────

    def get_quests(self) -> list:
        """Ambil daftar quest"""
        urls = [
            f"{ZEALY_V2}/public/communities/{COMMUNITY_SUBDOMAIN}/quests",
            f"{ZEALY_V1}/communities/{COMMUNITY_SUBDOMAIN}/quests",
        ]
        for url in urls:
            try:
                self._delay()
                resp = self._get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    quests = data if isinstance(data, list) else data.get("quests", [])
                    log.info(f"[{self.email}] 📋 {len(quests)} quest ditemukan")
                    return quests
            except Exception as e:
                log.debug(f"[{self.email}] get_quests error: {e}")
        return []

    def claim_quest(self, quest_id: str, quest_name: str = "",
                    is_twitter: bool = False) -> bool:
        """Claim satu quest"""
        url = f"{ZEALY_V2}/public/communities/{COMMUNITY_SUBDOMAIN}/quests/{quest_id}/claim"
        payload = {"twitterUsername": self.twitter_username} if is_twitter else {}

        try:
            self._delay()
            resp = self._post(url, payload)

            if resp.status_code in [200, 201]:
                xp = resp.json().get("xp", 0)
                log.info(f"[{self.email}] ✅ Quest '{quest_name}' claimed! +{xp} XP")
                return True
            if resp.status_code == 409:
                log.warning(f"[{self.email}] ⚠️ Quest '{quest_name}' sudah pernah di-claim")
                return True

            log.warning(f"[{self.email}] ⚠️ Claim '{quest_name}' gagal: {resp.status_code}")
            return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error claim_quest: {e}")
            return False

    def complete_quests(self) -> int:
        """Claim semua quest yang bisa di-automate"""
        quests = self.get_quests()
        completed = 0
        SKIP = ["discord", "snapshot", "manual", "wallet", "nft", "token"]

        for quest in quests:
            qid   = quest.get("id", "")
            qname = quest.get("name", quest.get("title", ""))
            qtype = quest.get("type", "").lower()
            if not qid:
                continue
            if any(t in qtype for t in SKIP):
                log.info(f"[{self.email}] ⏭️  Skip ({qtype}): {qname}")
                continue
            is_tw = "twitter" in qtype or "x.com" in qname.lower()
            if self.claim_quest(qid, qname, is_twitter=is_tw):
                completed += 1
            self._delay()

        return completed

    def get_user_xp(self) -> int:
        """Cek XP user saat ini"""
        if not self.user_id:
            return 0
        urls = [
            f"{ZEALY_V2}/public/communities/{COMMUNITY_SUBDOMAIN}/users/{self.user_id}",
            f"{ZEALY_V1}/communities/{COMMUNITY_SUBDOMAIN}/users/{self.user_id}",
        ]
        for url in urls:
            try:
                self._delay()
                resp = self._get(url)
                if resp.status_code == 200:
                    xp = resp.json().get("xp", 0)
                    log.info(f"[{self.email}] 📊 XP: {xp}")
                    return xp
            except Exception:
                continue
        return 0

    # ─────────────────────────────────────────────
    #  MAIN RUN
    # ─────────────────────────────────────────────

    def run(self, otp: str, turnstile_token: str) -> dict:
        """
        Jalankan full flow setelah OTP dan turnstile token tersedia.
        Dipanggil dari main.py.
        """
        result = {
            "email":   self.email,
            "twitter": self.twitter_username,
            "status":  "failed",
            "xp":      0,
            "message": ""
        }

        # Step 3: Verify OTP
        if not self.verify_otp(otp, turnstile_token):
            result["message"] = "Gagal verify OTP"
            return result
        self._delay()

        # Step 4: Set profile
        self.create_profile()
        self._delay()

        # Step 5: Join komunitas
        if not self.join_community():
            result["message"] = "Gagal join komunitas"
            return result
        self._delay()

        # Step 6: Complete quests
        completed = self.complete_quests()

        # Step 7: Cek XP
        xp = self.get_user_xp()

        result["status"]  = "success" if xp >= 1 else "partial"
        result["xp"]      = xp
        result["message"] = f"Selesai! {completed} quest claimed, XP: {xp}"
        return result
