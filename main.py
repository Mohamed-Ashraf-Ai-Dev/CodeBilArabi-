import os
import json
import requests
import random
import hashlib
import time
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
# PROMPT (The Brain)
# =========================================
def build_prompt(mode, history):
    history_titles = [h.get("title", "") if isinstance(h, dict) else str(h) for h in history[-20:]]

    return f"""
أنت مهندس برمجيات محترف (Senior Software Engineer) مصري، بتكتب لجمهور من المبرمجين المحترفين على تليجرام في قناة "CodeBilArabi".

الوضع (MODE): {mode}
المواضيع السابقة (ممنوع التكرار): {history_titles}
قائمة الممنوعات: {TOPIC_BLACKLIST}

التعليمات الصارمة:
1. اللغة: "عربي مهندسين" (مزيج بين العامية المصرية التقنية والمصطلحات الإنجليزية كما هي).
2. المحتوى: ادخل في الـ Deep Internals فوراً. ابعد عن الشرح الأكاديمي، ركز على الـ Trade-offs، الـ Performance، والـ Real-world bottlenecks.
3. الشخصية: أنت شخص خبير، لغتك مباشرة، بلاش مقدمات ترحيبية أو ختاميات "AI" زي "في الختام".
4. التنسيق: 
   السطر 1: [{mode}]
   السطر 2: عنوان تقني صايع (Technical Title)
   الباقي: المحتوى التقني مباشرة.

ملاحظة: لو الـ Mode هو "Elite Arena"، حط كود فيه Bug منطقي (Logic Bug) صعب، وقولهم "اكتب الحل في التعليقات".
ممنوع استخدام الفصحى المملة.
"""

# =========================================
# AI CALLS
# =========================================
def ask_ai(prompt):
    # نحاول نكلم OpenRouter الأول
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "google/gemma-2-27b-it",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1200
            },
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenRouter Failed, trying Groq... Error: {e}")
        # Fallback لـ Groq
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "max_tokens": 1200
            },
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

# =========================================
# VERIFICATION (The Filter)
# =========================================
def verify(content):
    v_prompt = f"""
أعد صياغة البوست التالي ليكون أكثر واقعية لمهندس برمجيات خبير. 
- احذف أي جمل تبدو وكأنها مكتوبة بواسطة ذكاء اصطناعي.
- اجعل المصطلحات التقنية بالإنجليزية (English).
- استخدم العامية المصرية التقنية (Tech Egyptian Slang).
- حافظ على العمق الهندسي.

البوست الأصلي:
{content}
"""
    try:
        return ask_ai(v_prompt)
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
        "parse_mode": "Markdown" 
    }
    try:
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except:
        return False

# =========================================
# GENERATION LOGIC
# =========================================
def generate(db):
    for attempt in range(5):
        print(f"Attempt {attempt + 1}...")
        mode = random.choice(CONTENT_MODES)
        prompt = build_prompt(mode, db["history"])
        
        content = ask_ai(prompt)
        content = verify(content)

        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if len(lines) < 2:
            continue

        title = lines[1]
        if is_duplicate(db, title):
            print(f"Duplicate found: {title}. Retrying...")
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
        print("Failed to generate unique content.")
        return

    final_post = f"{content}\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"

    if send(final_post):
        db["history"].append({
            "title": title,
            "mode": mode,
            "date": str(datetime.utcnow())
        })
        save_topic(db, title)
        save_database(db)
        print(f"Successfully posted: {title}")
    else:
        print("Failed to send message to Telegram.")

if __name__ == "__main__":
    run()
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
