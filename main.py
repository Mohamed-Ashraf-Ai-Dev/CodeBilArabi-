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

# =========================================
# FILES
# =========================================

DATABASE_FILE = "database.json"

# =========================================
# CONTENT MODES
# =========================================

CONTENT_MODES = [
    {
        "name": "War Story",
        "style": "Write like a senior engineer describing a real production incident.",
        "format": "Narrative technical breakdown."
    },
    {
        "name": "Architecture Breakdown",
        "style": "Deep engineering analysis of infrastructure or system design.",
        "format": "Concise architecture analysis."
    },
    {
        "name": "Performance Crime",
        "style": "Analyze terrible performance decisions and why they fail.",
        "format": "Aggressive technical critique."
    },
    {
        "name": "Myth Busting",
        "style": "Destroy a common engineering misconception.",
        "format": "Contrarian engineering post."
    },
    {
        "name": "Distributed Systems Chaos",
        "style": "Analyze distributed failure scenarios.",
        "format": "Failure-oriented analysis."
    },
    {
        "name": "Low-Level Internals",
        "style": "Deep dive into kernels, memory, CPU, networking, schedulers.",
        "format": "Hardcore systems internals."
    },
    {
        "name": "Security Research",
        "style": "Analyze realistic security architecture flaws and mitigations.",
        "format": "Defensive security analysis."
    },
    {
        "name": "Elite Arena",
        "style": "Create a subtle engineering puzzle.",
        "format": "Code challenge."
    },
    {
        "name": "Code Review Roast",
        "style": "Critique terrible engineering code professionally.",
        "format": "Code review."
    },
    {
        "name": "Failure Analysis",
        "style": "Analyze why a production system collapsed.",
        "format": "Postmortem style."
    }
]

# =========================================
# BLACKLIST
# =========================================

TOPIC_BLACKLIST = [
    "blockchain",
    "crypto moon",
    "web3",
    "AI will replace programmers",
    "generic microservices",
]

# =========================================
# DATABASE
# =========================================

def load_database():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "history": [],
                "topic_hashes": []
            }, f, ensure_ascii=False, indent=2)

    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_database(db):
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# =========================================
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
