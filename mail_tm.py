import re
import requests
import time
import random
import string
import logging

log = logging.getLogger(__name__)

MAILSLURP_API = "https://api.mailslurp.com"

# Common name words for generating human-like email usernames
FIRST_NAMES = ["john","james","michael","david","robert","william","richard","thomas","charles","daniel",
               "sarah","emily","jessica","ashley","jennifer","amanda","melissa","stephanie","lisa","nicole"]
LAST_NAMES  = ["smith","jones","williams","brown","davis","miller","wilson","moore","taylor","anderson",
               "jackson","white","harris","martin","thompson","garcia","martinez","robinson","clark","lewis"]


class MailTM:
    """
    MailSlurp email provider with WaitFor API.
    
    Key advantage: waitForLatestEmail is a LONG-POLL endpoint.
    It holds the HTTP connection open and returns INSTANTLY when email arrives.
    No polling loop needed — zero latency from email arrival to OTP extraction.
    
    This solves the OTP expiry problem completely.
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

    def _random_string(self, length: int = 8) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    def _human_username(self) -> str:
        """Generate a human-like email username to avoid UUID format rejection"""
        first = random.choice(FIRST_NAMES)
        last  = random.choice(LAST_NAMES)
        num   = random.randint(10, 999)
        # Patterns: john.smith92, jsmith_234, johnsmith99
        patterns = [
            f"{first}.{last}{num}",
            f"{first[0]}{last}{num}",
            f"{first}{last[0]}{num}",
            f"{first}_{last}{num}",
        ]
        return random.choice(patterns)

    # ──────────────────────────────────────────
    #  CREATE INBOX
    # ──────────────────────────────────────────

    def create_account(self) -> dict:
        """Create MailSlurp inbox with human-like username"""
        try:
            username = self._human_username()

            resp = self._session.post(
                f"{MAILSLURP_API}/inboxes",
                json={
                    "name":        f"zealy-{username}",
                    "emailAddress": username,
                    "expiresIn":   7200000,   # 2 hours in ms
                    "inboxType":   "HTTP_INBOX",
                }
            )
            data = resp.json()

            if resp.status_code not in [200, 201]:
                log.error(f"❌ MailSlurp error: {resp.status_code} - {data}")
                return {}

            self._inbox_id = data.get("id", "")
            raw_email      = data.get("emailAddress", "")
            self.password  = self._random_string(12)

            if not raw_email or not self._inbox_id:
                raise ValueError(f"Response tidak valid: {data}")

            # Use raw email if it looks normal, otherwise construct from username
            local = raw_email.split("@")[0] if "@" in raw_email else ""
            domain = raw_email.split("@")[-1] if "@" in raw_email else "mailslurp.com"

            if "-" in local and len(local) > 20:
                # Still UUID format - use our username with actual domain
                self.email = f"{username}@{domain}"
            else:
                self.email = raw_email

            log.info(f"✅ MailSlurp inbox: {self.email} (id: {self._inbox_id})")
            return {"email": self.email, "password": self.password}

        except Exception as e:
            log.error(f"❌ MailSlurp create error: {e}")
            return {}

    # ──────────────────────────────────────────
    #  WAIT FOR EMAIL (Long-Poll - INSTANT)
    # ──────────────────────────────────────────

    def find_otp_code(self, max_wait: int = 90) -> str:
        """
        Use MailSlurp waitForLatestEmail - LONG POLL.
        Single HTTP request that holds open until email arrives.
        Returns INSTANTLY when email arrives - no polling delay!
        """
        log.info(f"📬 Waiting for OTP via MailSlurp long-poll: {self.email}...")

        try:
            # waitForLatestEmail holds connection open until email arrives or timeout
            resp = self._session.get(
                f"{MAILSLURP_API}/waitForLatestEmail",
                params={
                    "inboxId":     self._inbox_id,
                    "timeout":     max_wait * 1000,  # ms
                    "unreadOnly":  True,
                },
                timeout=max_wait + 10  # slightly longer than server timeout
            )

            if resp.status_code == 200:
                data = resp.json()
                subject = data.get("subject", "")
                body    = data.get("body", "") or ""
                log.info(f"📧 MailSlurp email: {subject}")

                # Extract OTP from subject first (faster)
                otp = self._extract_otp(subject)
                if otp:
                    return otp

                # Then from body
                otp = self._extract_otp(body)
                if otp:
                    return otp

                log.warning(f"⚠️ Email received but no OTP found: {subject}")
                return ""

            elif resp.status_code == 408:
                log.warning(f"⚠️ MailSlurp timeout - no email in {max_wait}s")
                return ""
            else:
                log.error(f"❌ MailSlurp waitFor error: {resp.status_code} - {resp.text[:200]}")
                return ""

        except requests.Timeout:
            log.warning(f"⚠️ Request timeout waiting for email")
            return ""
        except Exception as e:
            log.error(f"❌ Error waiting for email: {e}")
            return ""

    def find_verification_link(self, max_wait: int = 90) -> str:
        """Find verification link from inbox"""
        try:
            resp = self._session.get(
                f"{MAILSLURP_API}/waitForLatestEmail",
                params={"inboxId": self._inbox_id, "timeout": max_wait * 1000, "unreadOnly": True},
                timeout=max_wait + 10
            )
            if resp.status_code == 200:
                body = resp.json().get("body", "") or ""
                for pat in [r'https://zealy\.io/verify[^\s"<>]+',
                            r'https://[^\s"<>]*zealy[^\s"<>]*verify[^\s"<>]+']:
                    m = re.findall(pat, body, re.IGNORECASE)
                    if m:
                        return m[0].rstrip(".")
        except Exception:
            pass
        return ""

    # ──────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────

    def _extract_otp(self, text: str) -> str:
        """Extract 6-char alphanumeric OTP (Zealy format: Z3Ge9A)"""
        if not text:
            return ""
        patterns = [
            r'login code is\s+([A-Za-z0-9]{6})',
            r'code is\s+([A-Za-z0-9]{6})',
            r'code[:\s]+([A-Za-z0-9]{6})\b',
            r'([A-Za-z0-9]{6})\s+is your',
            r'verification code[:\s]+([A-Za-z0-9]{6})',
            r'your code[:\s]+([A-Za-z0-9]{6})',
            r'<[^>]*>\s*([A-Za-z0-9]{6})\s*<',
            r'\b(\d{6})\b',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                otp = matches[0]
                if otp.lower() not in ['zealy', 'login', 'email', 'click', 'https']:
                    log.info(f"✅ OTP found: {otp}")
                    return otp
        return ""

    def delete_account(self):
        """Delete MailSlurp inbox after use"""
        if not self._inbox_id:
            return
        try:
            self._session.delete(f"{MAILSLURP_API}/inboxes/{self._inbox_id}")
            log.info(f"🗑️ Inbox {self.email} deleted")
        except Exception:
            pass
