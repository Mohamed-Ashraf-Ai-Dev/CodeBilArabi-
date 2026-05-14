import os
import json
import requests
import random

# المفاتيح
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    # أقسام عامة بدون أمثلة فرعية عشان الـ AI هو اللي يبتكر النقطة
    categories = [
        {"name": "System Architecture", "goal": "Explore complex distributed patterns and scalability trade-offs."},
        {"name": "Low-Level Internals", "goal": "Deep dive into OS kernels, memory management, or hardware-software interface."},
        {"name": "The Elite Arena (Hard Challenge)", "goal": "Create a coding puzzle with a very subtle logic bug or a performance bottleneck."},
        {"name": "Security & Exploitation", "goal": "Analyze a sophisticated vulnerability or a cryptographic weakness."},
        {"name": "Performance Forensics", "goal": "Investigate high-speed optimization or low-latency engineering."},
        {"name": "Distributed Systems Chaos", "goal": "Analyze consensus failure scenarios or network partition edge cases."}
    ]
    
    selected = random.choice(categories)
    
    # برومبت يمنع التقليد ويجبر الـ AI على الابتكار
    prompt = f"""
    You are a Senior Software Architect and a Security Researcher. 
    Category: {selected['name']}
    Goal: {selected['goal']}
    Recent Topics (DO NOT REPEAT): {history[-15:]}

    STRICT INSTRUCTIONS:
    1. INNOVATION: Do not use common or textbook examples. Invent or choose a niche, advanced technical sub-topic.
    2. LEVEL: Target the 1% of top senior engineers. Use raw, dense engineering facts.
    3. NO EXAMPLES: I have provided no examples because I want you to use your vast internal knowledge to select a unique topic.
    4. INTERACTION: 
       - If it's 'The Elite Arena', write a tricky code snippet (C++, Rust, Go, or Python) and end with "اكتب الحل في التعليقات".
       - If it's other categories, provide a high-level briefing that sparks a debate.
    5. LANGUAGE: Technical Arabic (Arabic sentences + English technical terms).
    6. FORMAT:
       Line 1: [{selected['name']}]
       Line 2: **Unique Technical Title**
       Lines 3+: Content only. No fluff. No introductions.
    """

    # محاولة OpenRouter أولاً
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9 # رفعنا الـ temperature لزيادة الابتكار
            }, timeout=30
        )
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        # البديل Groq
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8
                }, timeout=30
            )
            return res.json()['choices'][0]['message']['content'].strip()
        except:
            return None

def run_mission():
    if not os.path.exists("database.json"):
        with open("database.json", "w") as f:
            json.dump({"history": []}, f)

    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    content = get_ai_content(db["history"])
    
    if content:
        watermark = "\n\n━━━━━━━━━━━━━━\n🚀 **CodeBilArabi**"
        final_post = content + watermark
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # محاولة Markdown ثم Plain Text
        tg_res = requests.post(url, data={"chat_id": CHAT_ID, "text": final_post, "parse_mode": "Markdown"})
        if tg_res.status_code != 200:
            requests.post(url, data={"chat_id": CHAT_ID, "text": final_post})
            
        if tg_res.status_code == 200:
            lines = content.split('\n')
            db["history"].append(lines[1].strip() if len(lines) > 1 else lines[0].strip())
            with open("database.json", "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
