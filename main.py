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
    "blockchain", "crypto", "web3", "AI will replace programmers", "generic microservices", "طريقة عمل ويب سايت"
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
    db["topic_hashes"] = db["topic_hashes"][-300:]

# =========================================
# PROMPT - STRICT VERSION
# =========================================
def build_prompt(mode, history):
    history_titles = [h.get("title", "") if isinstance(h, dict) else str(h) for h in history[-20:]]

    return f"""
You are a Senior Software Engineer. Write a technical Telegram post for "CodeBilArabi".

MODE: {mode}
EXCLUDE TITLES: {history_titles}

STRICT RULES:
1. LANGUAGE: Egyptian Tech Slang (Ammiya) + English Technical terms.
2. NO PROSE: No "Welcome", No "Here is the post", No "Notes", No "In conclusion".
3. NO META: Do not explain what you did. Do not talk to the user.
4. TONE: Professional, experienced, direct.
5. FORMAT:
   Line 1: [{mode}]
   Line 2: Title
   Line 3+: Content

EXAMPLE:
[{mode}]
العنوان هنا
المحتوى التقني المركز مباشرة بدون رغي..
"""

# =========================================
# AI CORE
# =========================================
def ask_ai(prompt):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "google/gemma-2-27b-it",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8
            },
            timeout=60
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=60
        )
        return r.json()["choices"][0]["message"]["content"].strip()

def verify(content):
    # الفلتر ده مهمته يمسح أي كلام زيادة الـ AI بيحطه
    v_prompt = f"""
This is a Telegram post. CLEAN IT UP.
- Keep ONLY the post content.
- Delete any notes like "I have removed...", "Notes:", "ملاحظات".
- Ensure it starts with the [MODE] tag.
- If it's in Fusha (formal Arabic), change it to Egyptian Tech Slang.

POST TO CLEAN:
{content}
"""
    return ask_ai(v_prompt)

# =========================================
# RUNNER
# =========================================
def run():
    db = load_database()
    
    for _ in range(5):
        mode = random.choice(CONTENT_MODES)
        raw = ask_ai(build_prompt(mode, db["history"]))
        clean = verify(raw)

        # التحقق من الهيكل (Structure Check)
        lines = [l.strip() for l in clean.split("\n") if l.strip()]
        if len(lines) < 3 or not lines[0].startswith("["):
            continue

        title = lines[1]
        if is_duplicate(db, title):
            continue

        final = clean + "\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"
        
        # Telegram Send
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": final, "parse_mode": "Markdown"})
        
        if res.status_code == 200:
            db["history"].append({"title": title, "mode": mode, "date": str(datetime.utcnow())})
            save_topic(db, title)
            save_database(db)
            print(f"Success: {title}")
            return

if __name__ == "__main__":
    run()
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

def verify(content):
    v_prompt = f"""
راجع البوست ده كأنك مهندس مصري شغال في شركة كبيرة. 
1. امسح أي جملة فيها ريحة ذكاء اصطناعي أو ترحيب.
2. اقلب أي كلمة فصحى لعامية تقنية مصرية.
3. تأكد إن المصطلحات التقنية مكتوبة بالإنجليزية.
4. لو فيه رموز غريبة أو تنسيق زبالة صلحها.

البوست:
{content}
"""
    return ask_ai(v_prompt, model="google/gemma-2-27b-it")

# =========================================
# TELEGRAM & MAIN LOGIC
# =========================================
def send(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # تنظيف النص من أي Markdown قد يكسر تليجرام
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except:
        return False

def run():
    db = load_database()
    
    for _ in range(5):
        mode = random.choice(CONTENT_MODES)
        raw_content = ask_ai(build_prompt(mode, db["history"]))
        clean_content = verify(raw_content)

        lines = [l for l in clean_content.split("\n") if l.strip()]
        if len(lines) < 2: continue
        
        title = lines[1]
        if is_duplicate(db, title): continue

        final_post = clean_content + "\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"
        
        if send(final_post):
            db["history"].append({"title": title, "mode": mode, "date": str(datetime.utcnow())})
            save_topic(db, title)
            save_database(db)
            print(f"Posted: {title}")
            return
    
    print("Failed to generate or send.")

if __name__ == "__main__":
    run()
