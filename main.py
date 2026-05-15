import os
import json
import requests
import random
import hashlib
import sys
from datetime import datetime

# =========================================
# 1. CONFIG & ENV CHECK
# =========================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not all([OPENROUTER_API_KEY, GROQ_API_KEY, TELEGRAM_BOT_TOKEN, CHAT_ID]):
    print("❌ Error: Missing Environment Variables.")
    sys.exit(1)

DATABASE_FILE = "database.json"

CONTENT_MODES = [
    "War Story", "Architecture Breakdown", "Performance Crime",
    "Myth Busting", "Distributed Systems Chaos", "Low-Level Internals",
    "Security Research", "Elite Arena", "Code Review Roast", "Failure Analysis"
]

TOPIC_BLACKLIST = [
    "blockchain", "crypto", "web3", "AI will replace programmers", 
    "generic microservices", "طريقة عمل ويب سايت", "كورس برمجة"
]

# =========================================
# 2. DATABASE MANAGEMENT
# =========================================
def load_database():
    if not os.path.exists(DATABASE_FILE):
        return {"history": [], "topic_hashes": []}
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ DB Load Warning: {e}")
        return {"history": [], "topic_hashes": []}

def save_database(db):
    try:
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ DB Save Error: {e}")

def is_duplicate(db, title):
    h = hashlib.md5(title.strip().lower().encode()).hexdigest()
    return h in db["topic_hashes"]

def update_db(db, title, mode):
    h = hashlib.md5(title.strip().lower().encode()).hexdigest()
    db["topic_hashes"].append(h)
    db["history"].append({
        "title": title,
        "mode": mode,
        "date": str(datetime.utcnow())
    })
    # Keep DB lean (last 300 topics)
    db["topic_hashes"] = db["topic_hashes"][-300:]
    save_database(db)

# =========================================
# 3. AI ORCHESTRATION
# =========================================
def call_llm(prompt, provider="openrouter"):
    """محرك الاستدعاء مع نظام الـ Fallback"""
    if provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        payload = {
            "model": "google/gemma-2-27b-it", # موديل ممتاز في العامية المصرية
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85
        }
    else: # Groq Fallback
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.75
        }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ {provider} failed: {e}")
        return None

def build_expert_prompt(mode, db):
    history_context = ", ".join([h["title"] for h in db["history"][-15:]])
    return f"""
You are a Senior Software Engineer (Egyptian). Write a high-level technical post for Telegram channel "CodeBilArabi".

MODE: {mode}
ALREADY COVERED (DO NOT REPEAT): {history_context}
BLACKLIST (FORBIDDEN TOPICS): {TOPIC_BLACKLIST}

STRICT RULES:
1. STYLE: Egyptian Tech Slang (Ammiya) - use words like "لبسنا في الحيط", "الزتونة", "بص يا زميلي".
2. NO CHAT: No "Welcome", "Here is your post", or "Notes". Start immediately.
3. STRUCTURE:
   Line 1: [{mode}]
   Line 2: Catchy Technical Title (Mixed Eng/Ar)
   Line 3+: The Deep-Dive technical content.
4. CODE: Use Markdown code blocks if needed.
"""

def refine_and_clean(content):
    """تنظيف المحتوى من أي شوائب AI"""
    refine_prompt = f"""
راجع البوست ده:
1. امسح أي مقدمات أو خاتمة AI (زي "أتمنى يعجبكم").
2. اقلب أي كلمة فصحى لعامية تقنية مصرية.
3. اتأكد إن أول سطر هو المود [MODE].
4. شيل أي "ملاحظات" في الآخر.

POST:
{content}
"""
    # نحاول ننضفه باستخدام Groq كـ Verifier
    result = call_llm(refine_prompt, provider="groq")
    return result if result else content

# =========================================
# 4. TELEGRAM DISPATCHER
# =========================================
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=data)
        return r.status_code == 200
    except:
        return False

# =========================================
# 5. MAIN EXECUTION
# =========================================
def execute():
    db = load_database()
    print("🚀 Starting Content Generation...")

    for attempt in range(1, 6):
        print(f"🔄 Attempt {attempt}/5...")
        mode = random.choice(CONTENT_MODES)
        
        # 1. Generate
        raw_post = call_llm(build_expert_prompt(mode, db), provider="openrouter")
        if not raw_post:
            raw_post = call_llm(build_expert_prompt(mode, db), provider="groq")
            
        if not raw_post: continue

        # 2. Refine
        final_content = refine_and_clean(raw_post)
        
        # 3. Validate Structure
        lines = [l.strip() for l in final_content.split("\n") if l.strip()]
        if len(lines) < 3 or not lines[0].startswith("["):
            print("❌ Invalid Structure. Retrying...")
            continue

        title = lines[1]
        if is_duplicate(db, title):
            print(f"❌ Duplicate Title: {title}. Retrying...")
            continue

        # 4. Final Polish
        full_message = f"{final_content}\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"

        # 5. Send
        if send_to_telegram(full_message):
            print(f"✅ Posted Successfully: {title}")
            update_db(db, title, mode)
            return
        else:
            print("❌ Telegram Send Failed.")

    print("⚠️ All attempts failed.")

if __name__ == "__main__":
    execute()
