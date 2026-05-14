import re
import time
import random
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import (
    INVITE_LINK,
    COMMUNITY_SUBDOMAIN,
    USER_AGENT,
)

log = logging.getLogger(__name__)

ZEALY_SIGNUP_URL = "https://zealy.io/sign-up"
ZEALY_COMMUNITY_URL = f"https://zealy.io/cw/{COMMUNITY_SUBDOMAIN}/questboard"


class ZealyBrowser:
    """
    Zealy bot menggunakan Playwright browser automation.

    Flow:
      1. Buka halaman sign-up Zealy di browser headless
      2. Input email → Turnstile di-solve otomatis oleh browser nyata
      3. Zealy kirim OTP 6 digit ke inbox
      4. Bot baca OTP dari mail.tm
      5. Input OTP di browser → login berhasil
      6. Set username
      7. Join komunitas via invite link
      8. Complete quest yang bisa di-automate
    """

    def __init__(self, email: str, twitter_username: str, mail_tm=None, proxy: str = None):
        self.email = email
        self.twitter_username = twitter_username
        self.mail_tm = mail_tm   # MailTM instance untuk baca OTP
        self.proxy = proxy
        self.token = None
        self.user_id = None

    def _random_delay(self, min_ms=500, max_ms=1500):
        """Delay seperti manusia"""
        time.sleep(random.uniform(min_ms, max_ms) / 1000)

    def _human_type(self, page, selector: str, text: str):
        """Ketik teks seperti manusia (pelan-pelan)"""
        page.click(selector)
        self._random_delay(200, 400)
        for char in text:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.05, 0.15))

    def run(self) -> dict:
        """
        Jalankan seluruh flow bot via browser.
        Return dict result.
        """
        result = {
            "email": self.email,
            "twitter": self.twitter_username,
            "status": "failed",
            "xp": 0,
            "message": ""
        }

        proxy_config = None
        if self.proxy:
            # Format: http://user:pass@host:port atau http://host:port
            proxy_config = {"server": self.proxy}

        with sync_playwright() as p:
            # Launch browser headless
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
                proxy=proxy_config,
            )

            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="America/New_York",
                # Sembunyikan bahwa ini adalah playwright
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )

            # Sembunyikan webdriver flag
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                window.chrome = { runtime: {} };
            """)

            page = context.new_page()

            try:
                # ── STEP 1: Buka halaman sign-up ─────────────────
                log.info(f"[{self.email}] 🌐 Membuka halaman sign-up Zealy...")
                page.goto(ZEALY_SIGNUP_URL, wait_until="networkidle", timeout=30000)
                self._random_delay(1000, 2000)

                # ── STEP 2: Klik "Continue with email" ───────────
                log.info(f"[{self.email}] 📧 Mencari tombol email...")
                email_btn = self._find_email_button(page)
                if not email_btn:
                    result["message"] = "Tombol email tidak ditemukan"
                    return result

                email_btn.click()
                self._random_delay(800, 1200)

                # ── STEP 3: Input email ───────────────────────────
                log.info(f"[{self.email}] ✍️ Input email: {self.email}")
                email_input = self._find_email_input(page)
                if not email_input:
                    result["message"] = "Input email tidak ditemukan"
                    return result

                email_input.click()
                self._random_delay(300, 600)
                email_input.fill(self.email)
                self._random_delay(500, 800)

                # ── STEP 4: Submit form (Turnstile di-solve oleh browser) ──
                log.info(f"[{self.email}] 🔐 Submit email (Turnstile akan di-solve browser)...")
                submit_btn = self._find_submit_button(page)
                if submit_btn:
                    submit_btn.click()
                else:
                    page.keyboard.press("Enter")

                # Tunggu sampai halaman OTP muncul
                log.info(f"[{self.email}] ⏳ Menunggu halaman OTP...")
                otp_appeared = self._wait_for_otp_page(page)
                if not otp_appeared:
                    # Screenshot untuk debug
                    page.screenshot(path=f"/tmp/zealy_debug_{self.email[:8]}.png")
                    result["message"] = "Halaman OTP tidak muncul setelah submit email"
                    return result

                log.info(f"[{self.email}] ✅ Halaman OTP muncul!")

                # ── STEP 5: Baca OTP dari mail.tm ────────────────
                otp = ""
                if self.mail_tm:
                    log.info(f"[{self.email}] 📬 Menunggu OTP di inbox {self.email}...")
                    otp = self.mail_tm.find_otp_code(max_wait=90)

                if not otp:
                    result["message"] = "OTP tidak ditemukan di inbox"
                    return result

                log.info(f"[{self.email}] 🔑 OTP didapat: {otp}")

                # ── STEP 6: Input OTP di browser ──────────────────
                log.info(f"[{self.email}] ✍️ Input OTP...")
                otp_success = self._input_otp(page, otp)
                if not otp_success:
                    result["message"] = "Gagal input OTP di browser"
                    return result

                # Tunggu redirect setelah OTP berhasil
                self._random_delay(2000, 3000)

                # ── STEP 7: Cek login berhasil ────────────────────
                log.info(f"[{self.email}] 🔍 Mengecek status login...")
                logged_in = self._wait_for_login(page)
                if not logged_in:
                    result["message"] = "OTP tidak diterima atau login gagal"
                    return result

                log.info(f"[{self.email}] ✅ Login berhasil!")

                # ── STEP 8: Set username jika diminta ─────────────
                self._handle_username_setup(page)
                self._random_delay(1000, 2000)

                # ── STEP 9: Ambil token dari browser ─────────────
                self.token, self.user_id = self._extract_auth_token(page)
                log.info(f"[{self.email}] 🎫 Token: {'✅ didapat' if self.token else '❌ tidak ada'}")

                # ── STEP 10: Join komunitas via invite link ───────
                log.info(f"[{self.email}] 🔗 Join komunitas via invite link...")
                joined = self._join_community(page)
                self._random_delay(2000, 3000)

                # ── STEP 11: Complete quest ────────────────────────
                completed = 0
                if joined:
                    log.info(f"[{self.email}] 🎯 Mencoba complete quest...")
                    completed = self._complete_quests(page)

                # ── STEP 12: Ambil XP ─────────────────────────────
                xp = self._get_xp(page)
                log.info(f"[{self.email}] 📊 XP: {xp}")

                result["status"] = "success" if (joined or xp > 0) else "partial"
                result["xp"] = xp
                result["message"] = f"Selesai! Joined: {joined}, Quest: {completed}, XP: {xp}"

            except PlaywrightTimeout as e:
                log.error(f"[{self.email}] ❌ Timeout: {e}")
                result["message"] = f"Timeout: {str(e)[:100]}"
            except Exception as e:
                log.error(f"[{self.email}] ❌ Error: {e}")
                result["message"] = f"Error: {str(e)[:100]}"
            finally:
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass

        return result

    # ──────────────────────────────────────────────────────────
    #  HELPER METHODS
    # ──────────────────────────────────────────────────────────

    def _find_email_button(self, page):
        """Cari tombol 'Continue with email'"""
        selectors = [
            "button:has-text('email')",
            "button:has-text('Email')",
            "[data-testid='email-button']",
            "button:has-text('Continue with email')",
            "button:has-text('Sign up with email')",
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    log.info(f"[{self.email}] ✅ Email button found: {sel}")
                    return btn
            except Exception:
                continue
        log.warning(f"[{self.email}] ⚠️ Email button tidak ditemukan, coba langsung ke input...")
        return None

    def _find_email_input(self, page):
        """Cari input field email"""
        selectors = [
            "input[type='email']",
            "input[placeholder*='email' i]",
            "input[placeholder*='kenny@zealy' i]",
            "input[name='email']",
        ]
        for sel in selectors:
            try:
                inp = page.locator(sel).first
                if inp.is_visible(timeout=5000):
                    log.info(f"[{self.email}] ✅ Email input found: {sel}")
                    return inp
            except Exception:
                continue
        log.error(f"[{self.email}] ❌ Email input tidak ditemukan")
        return None

    def _find_submit_button(self, page):
        """Cari tombol submit/continue"""
        selectors = [
            "button[type='submit']",
            "button:has-text('Continue')",
            "button:has-text('Next')",
            "button:has-text('Send')",
            "button:has-text('Sign up')",
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    return btn
            except Exception:
                continue
        return None

    def _wait_for_otp_page(self, page, timeout: int = 20000) -> bool:
        """Tunggu sampai halaman OTP muncul"""
        otp_indicators = [
            "input[placeholder*='code' i]",
            "input[placeholder*='otp' i]",
            "input[type='number']",
            "input[inputmode='numeric']",
            "[data-input-otp]",
            "text=Check your inbox",
            "text=verify",
            "text=code",
        ]
        for sel in otp_indicators:
            try:
                page.wait_for_selector(sel, timeout=timeout)
                return True
            except PlaywrightTimeout:
                continue
            except Exception:
                continue

        # Cek URL juga
        try:
            page.wait_for_url("**/verify**", timeout=5000)
            return True
        except Exception:
            pass

        return False

    def _input_otp(self, page, otp: str) -> bool:
        """Input kode OTP di browser"""
        self._random_delay(500, 1000)

        # Coba berbagai selector untuk OTP input
        otp_selectors = [
            "[data-input-otp]",
            "input[placeholder*='code' i]",
            "input[placeholder*='otp' i]",
            "input[type='number']",
            "input[inputmode='numeric']",
            "input[maxlength='6']",
            "input[maxlength='1']",  # bisa per-digit
        ]

        for sel in otp_selectors:
            try:
                inputs = page.locator(sel).all()
                if not inputs:
                    continue

                # Kalau 1 input panjang (6 char sekaligus)
                if len(inputs) == 1:
                    inp = inputs[0]
                    if inp.is_visible(timeout=2000):
                        inp.click()
                        self._random_delay(200, 400)
                        inp.fill(otp)
                        self._random_delay(500, 800)
                        # Coba submit
                        submit = self._find_submit_button(page)
                        if submit and submit.is_visible():
                            submit.click()
                        else:
                            page.keyboard.press("Enter")
                        log.info(f"[{self.email}] ✅ OTP diinput (single field)")
                        return True

                # Kalau 6 input per digit
                if len(inputs) >= 6:
                    for i, digit in enumerate(otp[:6]):
                        if i < len(inputs) and inputs[i].is_visible():
                            inputs[i].click()
                            inputs[i].type(digit)
                            self._random_delay(100, 200)
                    self._random_delay(500, 800)
                    page.keyboard.press("Enter")
                    log.info(f"[{self.email}] ✅ OTP diinput (per-digit)")
                    return True

            except Exception as e:
                log.debug(f"[{self.email}] OTP selector '{sel}' gagal: {e}")
                continue

        # Fallback: ketik langsung via keyboard
        try:
            page.keyboard.type(otp)
            self._random_delay(500, 800)
            page.keyboard.press("Enter")
            log.info(f"[{self.email}] ✅ OTP diinput via keyboard")
            return True
        except Exception as e:
            log.error(f"[{self.email}] ❌ Gagal input OTP: {e}")
            return False

    def _wait_for_login(self, page, timeout: int = 15000) -> bool:
        """Tunggu sampai login berhasil (redirect ke dashboard)"""
        success_indicators = [
            "**/questboard**",
            "**/leaderboard**",
            "**/c/**",
            "**zealy.io/cw/**",
        ]

        # Tunggu redirect
        for pattern in success_indicators:
            try:
                page.wait_for_url(pattern, timeout=timeout)
                return True
            except PlaywrightTimeout:
                continue

        # Cek apakah ada elemen yang menunjukkan sudah login
        login_elements = [
            "[data-testid='user-avatar']",
            "button:has-text('Log out')",
            "button:has-text('Logout')",
            "text=My communities",
            "text=Explore",
        ]
        for sel in login_elements:
            try:
                if page.locator(sel).is_visible(timeout=3000):
                    return True
            except Exception:
                continue

        # Cek apakah masih di halaman OTP (berarti salah)
        current_url = page.url
        if "verify" in current_url or "sign-up" in current_url or "sign-in" in current_url:
            return False

        # Kalau sudah keluar dari halaman auth, anggap berhasil
        if "zealy.io" in current_url and "sign" not in current_url and "verify" not in current_url:
            return True

        return False

    def _handle_username_setup(self, page):
        """Handle form setup username jika muncul setelah login"""
        try:
            # Zealy kadang minta username setelah pertama kali login
            username_input = page.locator("input[placeholder*='username' i], input[name='username']").first
            if username_input.is_visible(timeout=5000):
                username = f"{self.twitter_username}{random.randint(100, 999)}"
                log.info(f"[{self.email}] 👤 Set username: {username}")
                username_input.fill(username)
                self._random_delay(500, 800)
                # Klik Next/Continue
                next_btn = self._find_submit_button(page)
                if next_btn and next_btn.is_visible():
                    next_btn.click()
                    self._random_delay(1000, 2000)
        except Exception:
            pass  # Username form tidak muncul, skip

    def _extract_auth_token(self, page) -> tuple:
        """Ambil JWT token dan user ID dari localStorage/cookies browser"""
        try:
            # Zealy simpan token di localStorage
            token = page.evaluate("""() => {
                // Coba berbagai key localStorage
                const keys = ['access_token', 'token', 'jwt', 'auth_token',
                              'zealy_token', 'user_token'];
                for (const key of keys) {
                    const val = localStorage.getItem(key);
                    if (val) return val;
                }
                // Coba semua key localStorage
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    const val = localStorage.getItem(key);
                    if (val && val.length > 50 && val.includes('.')) {
                        return val;  // Kemungkinan JWT
                    }
                }
                return null;
            }""")

            user_id = page.evaluate("""() => {
                const keys = ['user_id', 'userId', 'user_metadata'];
                for (const key of keys) {
                    const val = localStorage.getItem(key);
                    if (val) return val;
                }
                return null;
            }""")

            if token:
                log.info(f"[{self.email}] 🎫 Token extracted (length: {len(token)})")
            return token, user_id

        except Exception as e:
            log.debug(f"[{self.email}] Token extraction: {e}")
            return None, None

    def _join_community(self, page) -> bool:
        """Join komunitas via invite link"""
        try:
            log.info(f"[{self.email}] 🔗 Navigasi ke invite link...")
            page.goto(INVITE_LINK, wait_until="domcontentloaded", timeout=20000)
            self._random_delay(2000, 3000)

            # Cari tombol Join
            join_selectors = [
                "button:has-text('Join')",
                "button:has-text('Join community')",
                "button:has-text('Accept')",
                "[data-testid='join-button']",
            ]

            for sel in join_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=5000):
                        log.info(f"[{self.email}] 🔗 Klik tombol join: {sel}")
                        btn.click()
                        self._random_delay(2000, 3000)
                        log.info(f"[{self.email}] ✅ Join komunitas berhasil!")
                        return True
                except Exception:
                    continue

            # Kalau tidak ada tombol join, mungkin sudah di dalam komunitas
            current_url = page.url
            if COMMUNITY_SUBDOMAIN in current_url:
                log.info(f"[{self.email}] ✅ Sudah di dalam komunitas!")
                return True

            log.warning(f"[{self.email}] ⚠️ Tombol join tidak ditemukan, URL: {current_url}")
            return False

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error join community: {e}")
            return False

    def _complete_quests(self, page) -> int:
        """Navigate ke questboard dan complete quest yang tersedia"""
        completed = 0
        try:
            log.info(f"[{self.email}] 📋 Navigasi ke questboard...")
            page.goto(ZEALY_COMMUNITY_URL, wait_until="domcontentloaded", timeout=20000)
            self._random_delay(2000, 3000)

            # Cari dan klik quest yang tersedia
            quest_selectors = [
                "[data-testid='quest-card']",
                ".quest-card",
                "button:has-text('Claim')",
                "[class*='quest']",
            ]

            for sel in quest_selectors:
                try:
                    quests = page.locator(sel).all()
                    if not quests:
                        continue

                    log.info(f"[{self.email}] 🎯 Ditemukan {len(quests)} quest dengan selector: {sel}")

                    for quest in quests[:10]:  # Max 10 quest
                        try:
                            if quest.is_visible():
                                quest.click()
                                self._random_delay(1000, 2000)

                                # Cari tombol Claim
                                claim_btn = page.locator("button:has-text('Claim')").first
                                if claim_btn.is_visible(timeout=3000):
                                    claim_btn.click()
                                    self._random_delay(1000, 2000)
                                    completed += 1
                                    log.info(f"[{self.email}] ✅ Quest di-claim ({completed})")

                                # Tutup modal jika ada
                                close_btn = page.locator("button[aria-label='close'], button:has-text('Close')").first
                                if close_btn.is_visible(timeout=1000):
                                    close_btn.click()
                                    self._random_delay(500, 800)
                        except Exception:
                            continue
                    break  # Pakai selector pertama yang berhasil
                except Exception:
                    continue

        except Exception as e:
            log.error(f"[{self.email}] ❌ Error complete quests: {e}")

        return completed

    def _get_xp(self, page) -> int:
        """Coba ambil XP dari halaman"""
        try:
            xp_text = page.locator("[data-testid='xp'], .xp-value, text=/\\d+ XP/").first
            if xp_text.is_visible(timeout=3000):
                text = xp_text.inner_text()
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[0])
        except Exception:
            pass
        return 0
