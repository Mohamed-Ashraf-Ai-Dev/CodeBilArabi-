import os
import json
import requests
import random
import hashlib
from datetime import datetime

# =========================================
# ENV
# =========================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

DATABASE_FILE = "database.json"

# =========================================
# CONTENT MODES
# =========================================
CONTENT_MODES = [
    "War Story", "Architecture Breakdown", "Performance Crime",
    "Myth Busting", "Distributed Systems Chaos", "Low-Level Internals",
    "Security Research", "Elite Arena", "Code Review Roast", "Failure Analysis"
]

TOPIC_BLACKLIST = [
    "blockchain", "crypto", "web3", "AI will replace programmers", "generic microservices"
]

# =========================================
# DB
# =========================================
def load_database():
    if not os.path.exists(DATABASE_FILE):
        return {"history": [], "topic_hashes": []}
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"history": [], "topic_hashes": []}

def save_database(db):
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# =========================================
# HELPERS
# =========================================
def hash_text(text):
    return hashlib.md5(text.strip().lower().encode()).hexdigest()

def is_duplicate(db, title):
    return hash_text(title) in db["topic_hashes"]

def save_topic(db, title):
    db["topic_hashes"].append(hash_text(title))
    # Keep only last 300 hashes to save space
    db["topic_hashes"] = db["topic_hashes"][-300:]

# =========================================
# PROMPT
# =========================================
def build_prompt(mode, history):
    history_titles = []
    for h in history[-20:]:
        if isinstance(h, dict):
            history_titles.append(h.get("title", ""))
        else:
            history_titles.append(str(h))

    return f"""
You are a Senior Software Engineer writing Telegram technical posts.

MODE: {mode}
RECENT TOPICS: {history_titles}
BLACKLIST: {TOPIC_BLACKLIST}

RULES:
- No AI tone
- No filler
- No academic explanations
- Real engineering only
- Arabic + English technical terms
- Unique topic every time

FORMAT:
Line 1: [{mode}]
Line 2: Technical title
Rest: content only

SPECIAL:
If Elite Arena:
- include bugged code
- end with: "اكتب الحل في التعليقات"
"""

# =========================================
# AI CALL
# =========================================
def ask_openrouter(prompt):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "google/gemma-2-27b-it",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 1200
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def ask_groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 1200
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# =========================================
# VERIFICATION
# =========================================
def verify(content):
    prompt = f"Fix this engineering post: remove AI tone, improve realism, keep technical depth.\n\nPOST:\n{content}"
    try:
        # Try to use a faster/cheaper model for verification if needed
        return ask_groq(prompt)
    except:
        return content

# =========================================
# TELEGRAM
# =========================================
def send(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown" # Optional: to support code blocks
    }
    r = requests.post(url, data=payload)
    return r.status_code == 200

# =========================================
# GENERATION
# =========================================
def generate(db):
    for _ in range(5):
        mode = random.choice(CONTENT_MODES)
        prompt = build_prompt(mode, db["history"])
        
        try:
            content = ask_openrouter(prompt)
        except:
            try:
                content = ask_groq(prompt)
            except:
                continue

        content = verify(content)
        lines = content.split("\n")
        if len(lines) < 2:
            continue

        title = lines[1].strip()
        if is_duplicate(db, title):
            continue

        return content, title, mode
    return None, None, None

# =========================================
# MAIN
# =========================================
def run():
    db = load_database()
    content, title, mode = generate(db)

    if not content:
        print("No content generated")
        return

    final = f"{content}\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"

    if send(final):
        db["history"].append({
            "title": title,
            "mode": mode,
            "date": str(datetime.utcnow())
        })
        save_topic(db, title)
        save_database(db)
        print(f"Posted: {title}")
    else:
        print("Telegram failed")

# =========================================
# ENTRY
# =========================================
if __name__ == "__main__":
    run()
