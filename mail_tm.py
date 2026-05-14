import re
import imaplib
import email as emaillib
import time
import random
import string
import logging

log = logging.getLogger(__name__)


class MailTM:
    """
    Gmail + Alias email provider.
    Each account uses a unique alias: zealyref+TAG@gmail.com
    OTP is read via IMAP from the Gmail inbox.
    Note: Zealy ACCEPTS + alias format (OTP was received correctly before).
          The previous failure was OTP expiring due to delay, not invalid email.
    """

    def __init__(self):
        from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
        self.gmail_address  = GMAIL_ADDRESS
        self.gmail_password = GMAIL_APP_PASSWORD
        self.email      = None
        self.password   = None
        self._alias_tag = None

    def _random_string(self, length: int = 8) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    def create_account(self) -> dict:
        """
        Generate unique Gmail alias for each account.
        Format: zealyref+TAG@gmail.com
        All OTPs land in the same Gmail inbox — matched by TAG.
        """
        base   = self.gmail_address.split("@")[0]
        domain = self.gmail_address.split("@")[1]
        tag    = self._random_string(8)
        self._alias_tag = tag
        self.email      = f"{base}+{tag}@{domain}"
        self.password   = self._random_string(12)
        log.info(f"✅ Gmail alias dibuat: {self.email}")
        return {"email": self.email, "password": self.password}

    def find_otp_code(self, max_wait: int = 90) -> str:
        """Wait for OTP from Gmail inbox via IMAP. Match by alias tag."""
        log.info(f"📬 Menunggu OTP di Gmail: {self.email}...")
        elapsed  = 0
        interval = 3  # check every 3 seconds for faster OTP capture

        while elapsed < max_wait:
            otp = self._check_gmail_for_otp()
            if otp:
                return otp
            time.sleep(interval)
            elapsed += interval
            log.info(f"⏳ Menunggu OTP Gmail... ({elapsed}/{max_wait}s)")

        log.warning(f"⚠️ Timeout Gmail setelah {max_wait}s")
        return ""

    def _check_gmail_for_otp(self) -> str:
        """Check Gmail IMAP for Zealy OTP email matching our alias."""
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            imap.login(self.gmail_address, self.gmail_password)
            imap.select("INBOX")

            # Search for unseen Zealy emails first, then all
            _, msgs = imap.search(None, '(FROM "zealy.io" UNSEEN)')
            if not msgs or not msgs[0]:
                _, msgs = imap.search(None, '(FROM "zealy.io")')

            if not msgs or not msgs[0]:
                imap.logout()
                return ""

            mail_ids = msgs[0].split()
            # Check most recent emails first (last 10)
            for mail_id in reversed(mail_ids[-10:]):
                _, data = imap.fetch(mail_id, "(RFC822)")
                msg     = emaillib.message_from_bytes(data[0][1])
                subject = msg.get("Subject", "")
                to_addr = msg.get("To", "").lower()
                log.info(f"📧 Gmail: {subject} | To: {to_addr[:60]}")

                # Match by alias tag to get the RIGHT OTP for this account
                if self._alias_tag and self._alias_tag.lower() not in to_addr:
                    continue

                # Check subject first (fastest)
                otp = self._extract_otp(subject)
                if otp:
                    imap.store(mail_id, "+FLAGS", "\\Seen")
                    imap.logout()
                    return otp

                # Check body
                body = self._get_email_body(msg)
                otp  = self._extract_otp(body)
                if otp:
                    imap.store(mail_id, "+FLAGS", "\\Seen")
                    imap.logout()
                    return otp

            imap.logout()
            return ""

        except imaplib.IMAP4.error as e:
            log.error(f"❌ IMAP login gagal: {e}")
            log.error("💡 Pastikan GMAIL_APP_PASSWORD sudah di-set di config.py!")
            return ""
        except Exception as e:
            log.error(f"❌ Error cek Gmail: {e}")
            return ""

    def _get_email_body(self, msg) -> str:
        body = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype in ["text/plain", "text/html"]:
                        charset = part.get_content_charset() or "utf-8"
                        body += part.get_payload(decode=True).decode(charset, errors="ignore")
            else:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        except Exception as e:
            log.debug(f"get_email_body error: {e}")
        return body

    def find_verification_link(self, max_wait: int = 90) -> str:
        elapsed  = 0
        interval = 5
        while elapsed < max_wait:
            try:
                imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
                imap.login(self.gmail_address, self.gmail_password)
                imap.select("INBOX")
                _, msgs = imap.search(None, '(FROM "zealy.io" UNSEEN)')
                if msgs and msgs[0]:
                    for mid in reversed(msgs[0].split()[-5:]):
                        _, data = imap.fetch(mid, "(RFC822)")
                        msg  = emaillib.message_from_bytes(data[0][1])
                        body = self._get_email_body(msg)
                        for pat in [r'https://zealy\.io/verify[^\s"<>]+',
                                    r'https://[^\s"<>]*zealy[^\s"<>]*verify[^\s"<>]+']:
                            m = re.findall(pat, body, re.IGNORECASE)
                            if m:
                                imap.store(mid, "+FLAGS", "\\Seen")
                                imap.logout()
                                return m[0].rstrip(".")
                imap.logout()
            except Exception:
                pass
            time.sleep(interval)
            elapsed += interval
        return ""

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
                    log.info(f"✅ OTP ditemukan: {otp}")
                    return otp
        return ""

    def delete_account(self):
        """Gmail alias does not need to be deleted."""
        pass
