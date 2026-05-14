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
    "War Story",
    "Architecture Breakdown",
    "Performance Crime",
    "Myth Busting",
    "Distributed Systems Chaos",
    "Low-Level Internals",
    "Security Research",
    "Elite Arena",
    "Code Review Roast",
    "Failure Analysis"
]

TOPIC_BLACKLIST = [
    "blockchain",
    "crypto",
    "web3",
    "AI will replace programmers",
    "generic microservices"
]

# =========================================
# DB
# =========================================

def load_database():
    if not os.path.exists(DATABASE_FILE):
        return {"history": [], "topic_hashes": []}

    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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

RECENT TOPICS:
{history_titles}

BLACKLIST:
{TOPIC_BLACKLIST}

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

    prompt = f"""
Fix this engineering post:
- remove AI tone
- improve realism
- keep technical depth

POST:
{content}
"""

    try:
        return ask_openrouter(prompt)
    except:
        return content

# =========================================
# TELEGRAM
# =========================================

def send(text):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    return requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    }).status_code == 200

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
            content = ask_groq(prompt)

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

    final = content + "\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"

    if send(final):

        db["history"].append({
            "title": title,
            "mode": mode,
            "date": str(datetime.utcnow())
        })

        save_topic(db, title)
        save_database(db)

        print("Posted successfully")

    else:
        print("Telegram failed")

# =========================================
# ENTRY
# =========================================

if __name__ == "__main__":
    run()# =========================================
# HELPERS
# =========================================

def hash_text(text):
    return hashlib.md5(text.encode()).hexdigest()


def topic_exists(db, title):
    h = hash_text(title.lower())

    return h in db["topic_hashes"]


def save_topic(db, title):
    h = hash_text(title.lower())

    db["topic_hashes"].append(h)

    db["topic_hashes"] = db["topic_hashes"][-200:]

# =========================================
# STYLE RULES
# =========================================

ANTI_AI_RULES = """
STRICT ANTI-AI WRITING RULES:

- Do NOT sound like an academic article.
- Do NOT write generic educational explanations.
- Avoid phrases like:
  - يمكن استخدام
  - تعتبر
  - من الطرق
  - من المهم
  - في الأنظمة الحديثة
  - تهدف إلى
  - تعتمد على

- Write like a real engineer posting on Telegram.
- Use sharp technical observations.
- Prefer concrete engineering details.
- Avoid motivational tone.
- Avoid textbook structure.
- Avoid filler paragraphs.
"""

# =========================================
# PROMPT BUILDER
# =========================================

def build_prompt(mode, history):

    blacklist = "\n".join(TOPIC_BLACKLIST)

    return f"""
You are a Principal Engineer writing technical Telegram posts.

CONTENT MODE:
{mode['name']}

STYLE:
{mode['style']}

FORMAT:
{mode['format']}

RECENT TOPICS:
{history[-30:]}

BLACKLISTED TOPICS:
{blacklist}

{ANTI_AI_RULES}

RULES:

1. Technical accuracy is mandatory.
2. Avoid hallucinations.
3. Avoid buzzword stacking.
4. Prefer niche engineering details.
5. Use realistic infrastructure scenarios.
6. Use Arabic naturally with English technical terms.
7. Never write like ChatGPT.
8. Avoid repetitive sentence structure.
9. Avoid generic introductions.
10. Keep it concise but insightful.
11. Generate a UNIQUE topic.

SPECIAL MODE RULES:

IF mode == "Elite Arena":
- Write a tricky code snippet.
- Use Python, Rust, Go, or C++.
- Bug must be subtle.
- End with:
"اكتب الحل في التعليقات"

IF mode == "Code Review Roast":
- Show terrible code.
- Critique it brutally but technically.

IF mode == "War Story":
- Simulate a real production outage.
- Include root cause.

OUTPUT FORMAT:

Line 1:
[{mode['name']}]

Line 2:
Technical title only

Remaining lines:
Post content only
"""

# =========================================
# AI REQUESTS
# =========================================

def ask_openrouter(prompt):

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.55,
            "max_tokens": 1200
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def ask_groq(prompt):

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,
            "max_tokens": 1200
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()

# =========================================
# VERIFICATION
# =========================================

def verify_content(content):

    verification_prompt = f"""
Review this technical Telegram post.

TASKS:
- Remove AI-sounding phrases.
- Remove buzzword stacking.
- Fix weak engineering claims.
- Improve realism.
- Make the tone feel human.
- Preserve technical depth.

POST:
{content}
"""

    try:
        verified = ask_openrouter(verification_prompt)
        return verified

    except Exception:
        return content

# =========================================
# TELEGRAM
# =========================================

def send_telegram(text):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    response = requests.post(
        url,
        data=payload,
        timeout=30
    )

    return response.status_code == 200

# =========================================
# GENERATION
# =========================================

def generate_post(db):

    for _ in range(5):

        mode = random.choice(CONTENT_MODES)

        prompt = build_prompt(mode, db["history"])

        try:
            content = ask_openrouter(prompt)

        except Exception as e:

            print("OpenRouter failed:", e)

            try:
                content = ask_groq(prompt)

            except Exception as ex:
                print("Groq failed:", ex)
                continue

        content = verify_content(content)

        lines = content.split("\n")

        if len(lines) < 2:
            continue

        title = lines[1].strip()

        if topic_exists(db, title):
            print("Duplicate topic skipped.")
            continue

        return content, title

    return None, None

# =========================================
# MAIN
# =========================================

def run_mission():

    db = load_database()

    content, title = generate_post(db)

    if not content:
        print("Failed to generate unique content.")
        return

    watermark = "\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"

    final_post = content + watermark

    success = send_telegram(final_post)

    if not success:
        print("Telegram send failed.")
        return

    db["history"].append({
        "title": title,
        "date": str(datetime.utcnow())
    })

    db["history"] = db["history"][-100:]

    save_topic(db, title)

    save_database(db)

    print("Post sent successfully.")

# =========================================
# ENTRY
# =========================================

if __name__ == "__main__":
    run_mission()
