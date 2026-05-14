import re
import imaplib
import email
import random
import string
import time
import logging

log = logging.getLogger(__name__)


class MailTM:
    """
    Gmail + Alias email provider.

    Flow:
      1. Generate alias: alvaomegazr+abc123@gmail.com
      2. Zealy kirim OTP ke alias tersebut
      3. Bot baca inbox Gmail via IMAP → extract OTP
    """

    def __init__(self):
        from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
        self.gmail_address  = GMAIL_ADDRESS
        self.gmail_password = GMAIL_APP_PASSWORD

        self.email    = None
        self.password = None
        self._alias   = None

    def _random_string(self, length: int = 8) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choices(chars, k=length))

    def create_account(self) -> dict:
        """
        Generate Gmail alias baru.
        Format: username+RANDOM@gmail.com
        Semua email masuk ke inbox Gmail yang sama.
        """
        base   = self.gmail_address.split("@")[0]
        domain = self.gmail_address.split("@")[1]
        tag    = self._random_string(8)

        self._alias   = f"{base}+{tag}@{domain}"
        self.email    = self._alias
        self.password = self._random_string(12)  # dummy

        log.info(f"✅ Gmail alias dibuat: {self._alias}")
        return {"email": self._alias, "password": self.password}

    # ──────────────────────────────────────────
    #  OTP READER via IMAP
    # ──────────────────────────────────────────

    def find_otp_code(self, max_wait: int = 90) -> str:
        """Tunggu dan baca OTP dari Gmail inbox via IMAP"""
        log.info(f"📬 Menunggu OTP di Gmail: {self._alias}...")

        elapsed  = 0
        interval = 5

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
        """Buka Gmail via IMAP dan cari email OTP dari Zealy"""
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            imap.login(self.gmail_address, self.gmail_password)
            imap.select("INBOX")

            # Cari email dari zealy.io yang belum dibaca
            _, msgs = imap.search(None, '(FROM "zealy.io" UNSEEN)')
            if not msgs or not msgs[0]:
                _, msgs = imap.search(None, '(FROM "zealy.io")')

            if not msgs or not msgs[0]:
                imap.logout()
                return ""

            mail_ids = msgs[0].split()
            for mail_id in reversed(mail_ids[-5:]):
                _, data = imap.fetch(mail_id, "(RFC822)")
                msg  = email.message_from_bytes(data[0][1])

                subject  = msg.get("Subject", "")
                to_addr  = msg.get("To", "").lower()
                log.info(f"📧 Gmail: {subject} | To: {to_addr[:60]}")

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
            log.error("💡 Pastikan App Password Gmail sudah di-set di config.py!")
            return ""
        except Exception as e:
            log.error(f"❌ Error cek Gmail: {e}")
            return ""

    def _get_email_body(self, msg) -> str:
        """Extract body text dari email"""
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

    def find_verification_link(self, max_wait: int = 90) -> str:
        """Cari link verifikasi (fallback)"""
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
                        msg  = email.message_from_bytes(data[0][1])
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

    def delete_account(self):
        """Gmail alias tidak perlu dihapus"""
        pass
