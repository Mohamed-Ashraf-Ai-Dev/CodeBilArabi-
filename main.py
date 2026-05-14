import os
import json
import requests
import random
import time

# ==============================
# ENV VARIABLES
# ==============================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ==============================
# CONFIG
# ==============================

DATABASE_FILE = "database.json"

CATEGORIES = [
    {
        "name": "System Architecture",
        "goal": "Explore complex distributed patterns and scalability trade-offs."
    },
    {
        "name": "Low-Level Internals",
        "goal": "Deep dive into OS kernels, memory management, or hardware-software interaction."
    },
    {
        "name": "The Elite Arena (Hard Challenge)",
        "goal": "Create a difficult engineering puzzle with subtle logic flaws or performance traps."
    },
    {
        "name": "Security Research",
        "goal": "Analyze realistic software security flaws and defensive engineering techniques."
    },
    {
        "name": "Performance Forensics",
        "goal": "Investigate high-performance bottlenecks and latency anomalies."
    },
    {
        "name": "Distributed Systems Chaos",
        "goal": "Analyze consensus failures and distributed edge cases."
    }
]

# ==============================
# DATABASE
# ==============================

def load_database():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump({"history": []}, f, ensure_ascii=False, indent=2)

    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_database(db):
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ==============================
# PROMPT BUILDER
# ==============================

def build_prompt(category, history):
    return f"""
You are a Principal Software Engineer and Systems Researcher.

Category:
{category['name']}

Goal:
{category['goal']}

Recent Topics:
{history[-20:]}

STRICT RULES:

1. Technical accuracy is mandatory.
2. Do NOT stack unrelated buzzwords.
3. Avoid fake relationships between concepts.
4. Prefer depth over hype.
5. Use realistic engineering scenarios.
6. If discussing security:
   - Focus on architecture and defense.
   - No offensive exploitation steps.
7. Avoid generic motivational language.
8. Use concise but dense technical writing.
9. Use Arabic + English technical terminology naturally.
10. Generate UNIQUE topics every time.

FORMAT:

Line 1:
[{category['name']}]

Line 2:
**Unique Technical Title**

Remaining Lines:
Technical content only.

SPECIAL RULE:
If category == "The Elite Arena (Hard Challenge)":
- Include a short tricky code snippet.
- Use C++, Rust, Go, or Python.
- End with:
"اكتب الحل في التعليقات"
"""


# ==============================
# AI REQUEST
# ==============================

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
            "temperature": 0.45,
            "max_tokens": 900
        },
        timeout=45
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
            "temperature": 0.4,
            "max_tokens": 900
        },
        timeout=45
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


# ==============================
# SELF VERIFICATION
# ==============================

def verify_content(content):
    verification_prompt = f"""
Review the following technical post.

TASKS:
1. Detect hallucinations.
2. Detect buzzword stacking.
3. Detect inaccurate cybersecurity claims.
4. Detect fake relationships between technologies.
5. Rewrite weak sections professionally.

RULES:
- Keep the same tone.
- Keep it advanced.
- Keep it concise.
- Ensure technical correctness.

POST:
{content}
"""

    try:
        verified = ask_openrouter(verification_prompt)
        return verified
    except Exception as e:
        print("Verification failed:", e)
        return content


# ==============================
# TELEGRAM
# ==============================

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    response = requests.post(url, data=payload, timeout=30)

    return response.status_code == 200


# ==============================
# MAIN GENERATION
# ==============================

def generate_post(history):
    category = random.choice(CATEGORIES)

    prompt = build_prompt(category, history)

    try:
        print("Using OpenRouter...")
        content = ask_openrouter(prompt)

    except Exception as e:
        print("OpenRouter failed:", e)

        try:
            print("Using Groq fallback...")
            content = ask_groq(prompt)

        except Exception as ex:
            print("Groq failed:", ex)
            return None

    verified_content = verify_content(content)

    return verified_content


# ==============================
# MAIN MISSION
# ==============================

def run_mission():
    db = load_database()

    content = generate_post(db["history"])

    if not content:
        print("Failed to generate content.")
        return

    watermark = "\n\n━━━━━━━━━━━━━━\n🚀 CodeBilArabi"

    final_post = content + watermark

    success = send_telegram_message(final_post)

    if success:
        print("Post sent successfully.")

        lines = content.split("\n")

        if len(lines) > 1:
            title = lines[1].strip()
        else:
            title = lines[0].strip()

        db["history"].append(title)

        db["history"] = db["history"][-50:]

        save_database(db)

    else:
        print("Telegram send failed.")


# ==============================
# ENTRY
# ==============================

if __name__ == "__main__":
    run_mission()
