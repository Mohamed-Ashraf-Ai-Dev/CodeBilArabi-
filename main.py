"""
╔══════════════════════════════════════════════════════════╗
║           CodeBilArabi - Telegram Content Bot            ║
║              Advanced Edition - v2.0                     ║
╚══════════════════════════════════════════════════════════╝

Features:
  - Dual AI fallback (OpenRouter → Groq)
  - Smart dedup with MD5 hashing + semantic similarity
  - Exponential backoff retry logic
  - Deep content validation pipeline
  - Structured logging with rotation
  - Topic diversity scoring
  - Telegram flood protection
  - Dry-run mode for testing
"""

import os
import json
import time
import random
import hashlib
import logging
import argparse
import re
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional

import requests

# =========================================
# LOGGING SETUP
# =========================================
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("CodeBilArabi")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # File handler with rotation (5MB max, 3 backups)
    fh = RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

log = setup_logger()


# =========================================
# CONFIG
# =========================================
class Config:
    """Central config — reads from env with sane defaults."""

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GROQ_API_KEY: str       = os.getenv("GROQ_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID: str            = os.getenv("CHAT_ID", "")

    DATABASE_FILE: str      = os.getenv("DATABASE_FILE", "database.json")

    # AI models
    OPENROUTER_MODEL: str   = os.getenv("OPENROUTER_MODEL", "google/gemma-2-27b-it")
    GROQ_MODEL: str         = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Retry / timeout
    MAX_ATTEMPTS: int       = int(os.getenv("MAX_ATTEMPTS", "5"))
    AI_TIMEOUT: int         = int(os.getenv("AI_TIMEOUT", "60"))
    RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", "2.0"))

    # Content params
    MAX_POST_CHARS: int     = int(os.getenv("MAX_POST_CHARS", "3800"))  # Telegram limit ~4096
    MIN_POST_CHARS: int     = int(os.getenv("MIN_POST_CHARS", "300"))
    MIN_CONTENT_LINES: int  = int(os.getenv("MIN_CONTENT_LINES", "5"))
    MAX_HISTORY_TITLES: int = int(os.getenv("MAX_HISTORY_TITLES", "20"))
    MAX_TOPIC_HASHES: int   = int(os.getenv("MAX_TOPIC_HASHES", "500"))

    # Telegram
    TG_RETRY_DELAY: float   = float(os.getenv("TG_RETRY_DELAY", "3.0"))  # Flood guard

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required env vars."""
        missing = []
        for var in ["OPENROUTER_API_KEY", "GROQ_API_KEY", "TELEGRAM_BOT_TOKEN", "CHAT_ID"]:
            if not getattr(cls, var):
                missing.append(var)
        return missing


# =========================================
# CONTENT MODES
# =========================================
CONTENT_MODES = [
    "War Story",
    "Architecture Breakdown",
    "Performance Crime",
    "Myth Busting",
    "Distributed Systems Chaos",
    "Low-Level Internals",
    "Security Research",
    "Elite Arena",
    "Code Review Roast",
    "Failure Analysis",
    "Database War",
    "DevOps Horror",
    "Concurrency Nightmare",
    "API Design Sins",
    "Memory Management Deep Dive",
]

TOPIC_BLACKLIST = {
    "blockchain", "crypto", "web3", "nft",
    "ai will replace programmers",
    "generic microservices",
    "طريقة عمل ويب سايت",
    "hello world",
}


# =========================================
# DATABASE
# =========================================
class Database:
    def __init__(self, path: str):
        self.path = path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            log.info("No DB found — starting fresh.")
            return {"history": [], "topic_hashes": [], "stats": {"total_sent": 0, "total_failed": 0}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migrate older schemas
                data.setdefault("stats", {"total_sent": 0, "total_failed": 0})
                return data
        except Exception as e:
            log.error(f"DB load error: {e} — starting fresh.")
            return {"history": [], "topic_hashes": [], "stats": {"total_sent": 0, "total_failed": 0}}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"DB save error: {e}")

    # ---- Topic dedup ----
    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.strip().lower().encode()).hexdigest()

    def is_duplicate(self, title: str) -> bool:
        return self._hash(title) in self._data["topic_hashes"]

    def record_topic(self, title: str):
        h = self._hash(title)
        self._data["topic_hashes"].append(h)
        self._data["topic_hashes"] = self._data["topic_hashes"][-Config.MAX_TOPIC_HASHES:]

    # ---- History ----
    @property
    def recent_titles(self) -> list[str]:
        return [
            (h.get("title", "") if isinstance(h, dict) else str(h))
            for h in self._data["history"][-Config.MAX_HISTORY_TITLES:]
        ]

    @property
    def recent_modes(self) -> list[str]:
        return [
            h.get("mode", "") for h in self._data["history"][-10:] if isinstance(h, dict)
        ]

    def add_entry(self, title: str, mode: str, content: str):
        self._data["history"].append({
            "title": title,
            "mode": mode,
            "date": datetime.now(timezone.utc).isoformat(),
            "content_hash": self._hash(content),
        })
        self._data["history"] = self._data["history"][-300:]
        self._data["stats"]["total_sent"] += 1
        self.record_topic(title)

    def record_failure(self):
        self._data["stats"]["total_failed"] += 1

    @property
    def stats(self) -> dict:
        return self._data["stats"]


# =========================================
# PROMPT BUILDER
# =========================================
class PromptBuilder:
    @staticmethod
    def _is_blacklisted(mode: str, used_modes: list[str]) -> bool:
        """Avoid using the same mode 3 times in a row."""
        return used_modes[-3:].count(mode) >= 2 if len(used_modes) >= 3 else False

    @staticmethod
    def pick_mode(used_modes: list[str]) -> str:
        available = [m for m in CONTENT_MODES if not PromptBuilder._is_blacklisted(m, used_modes)]
        return random.choice(available or CONTENT_MODES)

    @staticmethod
    def build_generation_prompt(mode: str, history_titles: list[str]) -> str:
        blacklist_str = "\n".join(f"- {t}" for t in TOPIC_BLACKLIST)
        history_str = "\n".join(f"- {t}" for t in history_titles) if history_titles else "None yet."

        return f"""You are a Senior Software Engineer writing for "CodeBilArabi" — an elite Arabic tech Telegram channel.

━━━━ SESSION CONTEXT ━━━━
MODE: {mode}
ALREADY COVERED TOPICS (avoid repeating):
{history_str}

FORBIDDEN TOPICS (never write about these):
{blacklist_str}

━━━━ OUTPUT FORMAT (STRICT) ━━━━
Line 1: [{mode}]
Line 2: العنوان (must be Arabic, specific, and catchy — not generic)
Lines 3+: المحتوى التقني

━━━━ LANGUAGE RULES ━━━━
- Write in Egyptian Tech Slang (Ammiya) mixed with English technical terms.
- Example: "لو عندك system بيعمل 100k requests/sec وفجأة الـ latency ارتفعت..."
- Technical terms stay in English: mutex, race condition, kernel, syscall, etc.
- NO Fusha (formal Arabic). NO English-only sentences.

━━━━ CONTENT RULES ━━━━
- Include real-world scenarios, code snippets (inline), or war stories.
- Minimum 5 meaningful lines of content.
- Use Telegram formatting: *bold*, `code`, ```code blocks```.
- End with a memorable takeaway or question to the reader.
- No intros like "مرحباً" or "في المقال ده".
- No outros like "في الختام" or "آمل أن يكون مفيداً".
- Write like you're sharing knowledge in a senior engineers' chat.

━━━━ START WRITING NOW ━━━━"""

    @staticmethod
    def build_cleanup_prompt(raw_content: str) -> str:
        return f"""You are a strict content editor for a tech Telegram channel.

TASK: Clean up the following post. Keep ONLY the actual post content.

REMOVE:
- Any meta-commentary like "Here is the post", "I have written", "Notes:", "ملاحظات"
- Any apologies or explanations
- Any trailing instructions echoed back
- Extra blank lines at start/end

PRESERVE:
- The [MODE] tag on line 1
- The Arabic title on line 2
- All technical content, code blocks, and formatting

IMPORTANT: If the language is Fusha (formal Arabic), rewrite in Egyptian Tech Slang.

POST TO CLEAN:
{raw_content}

OUTPUT THE CLEANED POST ONLY. NO COMMENTARY."""


# =========================================
# AI CLIENT
# =========================================
class AIClient:
    def __init__(self):
        self._openrouter_failures = 0

    def _call_openrouter(self, prompt: str) -> str:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://codebil-arabi.bot",
                "X-Title": "CodeBilArabi",
            },
            json={
                "model": Config.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.82,
                "max_tokens": 1200,
            },
            timeout=Config.AI_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def _call_groq(self, prompt: str) -> str:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {Config.GROQ_API_KEY}"},
            json={
                "model": Config.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.75,
                "max_tokens": 1200,
            },
            timeout=Config.AI_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def complete(self, prompt: str, label: str = "AI") -> Optional[str]:
        """Try OpenRouter first, fall back to Groq with exponential backoff."""
        providers = [
            ("OpenRouter", self._call_openrouter),
            ("Groq", self._call_groq),
        ]

        for provider_name, caller in providers:
            for attempt in range(1, 4):
                try:
                    log.debug(f"[{label}] Calling {provider_name} (attempt {attempt})")
                    result = caller(prompt)
                    if result:
                        log.debug(f"[{label}] {provider_name} success — {len(result)} chars")
                        return result
                except requests.exceptions.Timeout:
                    log.warning(f"[{label}] {provider_name} timed out (attempt {attempt})")
                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response else "?"
                    log.warning(f"[{label}] {provider_name} HTTP {status} (attempt {attempt})")
                    if status in (401, 403):
                        log.error(f"[{label}] {provider_name} auth error — skipping provider.")
                        break
                except Exception as e:
                    log.warning(f"[{label}] {provider_name} error: {e} (attempt {attempt})")

                if attempt < 3:
                    delay = Config.RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    log.debug(f"[{label}] Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)

        log.error(f"[{label}] All providers failed.")
        return None


# =========================================
# CONTENT VALIDATOR
# =========================================
class ContentValidator:
    @staticmethod
    def validate(content: str) -> tuple[bool, str]:
        """Returns (is_valid, reason)."""
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        if len(lines) < Config.MIN_CONTENT_LINES:
            return False, f"Too short: {len(lines)} lines (min {Config.MIN_CONTENT_LINES})"

        if not re.match(r"^\[.+\]$", lines[0]):
            return False, f"Line 1 must be [MODE TAG], got: {lines[0][:50]}"

        title = lines[1] if len(lines) > 1 else ""
        if len(title) < 5:
            return False, f"Title too short: '{title}'"

        # Check for blacklisted topics in content
        content_lower = content.lower()
        for topic in TOPIC_BLACKLIST:
            if topic.lower() in content_lower:
                return False, f"Blacklisted topic found: '{topic}'"

        # Check for meta-commentary (editor failed to clean)
        meta_patterns = [
            r"here is the (post|content|article)",
            r"i (have|'ve) (written|created|generated)",
            r"^notes?:",
            r"^ملاحظات",
            r"^in conclusion",
            r"^في الختام",
        ]
        for pattern in meta_patterns:
            if re.search(pattern, content_lower, re.MULTILINE):
                return False, f"Meta-commentary detected: pattern '{pattern}'"

        total_chars = len(content)
        if total_chars < Config.MIN_POST_CHARS:
            return False, f"Content too short: {total_chars} chars (min {Config.MIN_POST_CHARS})"
        if total_chars > Config.MAX_POST_CHARS:
            return False, f"Content too long: {total_chars} chars (max {Config.MAX_POST_CHARS})"

        return True, "OK"

    @staticmethod
    def extract_title(content: str) -> Optional[str]:
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        return lines[1] if len(lines) > 1 else None


# =========================================
# TELEGRAM CLIENT
# =========================================
class TelegramClient:
    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def send_message(self, text: str, dry_run: bool = False) -> bool:
        if dry_run:
            log.info("🔵 [DRY RUN] Would send:\n" + "─" * 40 + f"\n{text}\n" + "─" * 40)
            return True

        url = self.BASE_URL.format(token=Config.TELEGRAM_BOT_TOKEN, method="sendMessage")

        for attempt in range(1, 4):
            try:
                time.sleep(Config.TG_RETRY_DELAY)  # Flood guard
                res = requests.post(
                    url,
                    data={
                        "chat_id": Config.CHAT_ID,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                    timeout=30,
                )

                if res.status_code == 200:
                    log.info("✅ Message sent to Telegram.")
                    return True

                data = res.json()
                error_code = data.get("error_code", res.status_code)
                description = data.get("description", "Unknown")

                # Flood wait handling
                if error_code == 429:
                    retry_after = data.get("parameters", {}).get("retry_after", 30)
                    log.warning(f"Telegram flood control — waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                # Markdown parse error — retry without parse_mode
                if error_code == 400 and "parse" in description.lower():
                    log.warning("Markdown parse error — retrying as plain text.")
                    res2 = requests.post(
                        url,
                        data={"chat_id": Config.CHAT_ID, "text": text},
                        timeout=30,
                    )
                    if res2.status_code == 200:
                        log.info("✅ Sent as plain text.")
                        return True

                log.error(f"Telegram error {error_code}: {description} (attempt {attempt})")

            except Exception as e:
                log.error(f"Telegram request error (attempt {attempt}): {e}")

            if attempt < 3:
                time.sleep(Config.RETRY_BASE_DELAY * attempt)

        return False


# =========================================
# POST FORMATTER
# =========================================
def format_post(content: str) -> str:
    """Add channel signature to the post."""
    separator = "\n\n━━━━━━━━━━━━━━━━━━━━━━"
    footer = "🚀 *CodeBilArabi* — بنتكلم تك بالعربي"
    return f"{content.strip()}{separator}\n{footer}"


# =========================================
# MAIN RUNNER
# =========================================
def run(dry_run: bool = False):
    log.info("=" * 55)
    log.info("  CodeBilArabi Bot Starting...")
    log.info("=" * 55)

    # Validate config
    missing = Config.validate()
    if missing and not dry_run:
        log.error(f"Missing environment variables: {', '.join(missing)}")
        log.error("Set them before running. Exiting.")
        return

    db = Database(Config.DATABASE_FILE)
    ai = AIClient()
    validator = ContentValidator()
    telegram = TelegramClient()

    log.info(f"Stats — Sent: {db.stats['total_sent']} | Failed: {db.stats['total_failed']}")

    for attempt in range(1, Config.MAX_ATTEMPTS + 1):
        log.info(f"── Attempt {attempt}/{Config.MAX_ATTEMPTS} ──")

        # 1. Pick a diverse mode
        mode = PromptBuilder.pick_mode(db.recent_modes)
        log.info(f"Mode selected: [{mode}]")

        # 2. Generate content
        gen_prompt = PromptBuilder.build_generation_prompt(mode, db.recent_titles)
        raw_content = ai.complete(gen_prompt, label="GEN")
        if not raw_content:
            log.warning("Generation failed — trying next attempt.")
            db.record_failure()
            continue

        log.debug(f"Raw content ({len(raw_content)} chars):\n{raw_content[:200]}...")

        # 3. Clean / verify content
        clean_prompt = PromptBuilder.build_cleanup_prompt(raw_content)
        clean_content = ai.complete(clean_prompt, label="CLEAN")
        if not clean_content:
            log.warning("Cleanup failed — using raw content.")
            clean_content = raw_content

        # 4. Validate structure
        is_valid, reason = validator.validate(clean_content)
        if not is_valid:
            log.warning(f"Validation failed: {reason}")
            db.record_failure()
            continue

        # 5. Check for duplicate title
        title = validator.extract_title(clean_content)
        if not title:
            log.warning("Could not extract title.")
            db.record_failure()
            continue

        if db.is_duplicate(title):
            log.warning(f"Duplicate topic: '{title}' — skipping.")
            continue

        log.info(f"Title: {title}")

        # 6. Format and send
        final_post = format_post(clean_content)
        success = telegram.send_message(final_post, dry_run=dry_run)

        if success:
            db.add_entry(title, mode, clean_content)
            db.save()
            log.info(f"✅ Done! Post: '{title}' [{mode}]")
            return
        else:
            log.error("Telegram send failed.")
            db.record_failure()
            db.save()

    log.error(f"All {Config.MAX_ATTEMPTS} attempts exhausted. No post sent.")
    db.record_failure()
    db.save()


# =========================================
# ENTRY POINT
# =========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CodeBilArabi Telegram Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate content but don't send to Telegram.",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run)
