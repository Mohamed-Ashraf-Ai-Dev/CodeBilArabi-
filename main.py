import os
import json
import requests
import random

# المفاتيح من الـ Secrets
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    recent_history = history[-50:]
    
    # المحاور التقنية اللي اتفقنا عليها
    categories = [
        {"name": "System Design", "desc": "Advanced architectural patterns (Scalability, Fault Tolerance)."},
        {"name": "Deep Dive", "desc": "Low-level internals (Compilers, OS Kernels, Memory Management)."},
        {"name": "Logic Bug Challenge", "desc": "Tricky code snippet with a subtle logic flaw for seniors to solve."},
        {"name": "Complete The Code", "desc": "Complex function with a missing core logic part (Async, Crypto, etc.)."},
        {"name": "Network Internals", "desc": "High-performance networking (QUIC, TCP tuning, eBPF)."}
    ]
    
    selected = random.choice(categories)
    
    # برومبت إنجليزي لضمان أعلى جودة تفكير، مع أمر صريح بالمخرجات العربية
    prompt = f"""
    Act as an Elite Software Architect. Write a technical post for 'CodeBilArabi'.
    Category: {selected['name']} ({selected['desc']})
    Avoid: {recent_history}

    STRICT RULES:
    1. Language: Technical Arabic (Sentences in Arabic, core terms in English).
    2. No "Zatona" or "Ahlan". Start directly with the content.
    3. Format:
       Line 1: [{selected['name']}]
       Line 2: **Bold Technical Title**
       Line 3-6: 3 to 4 dense bullet points (Logic-focused, not general info).
    4. If Challenge: Include the code snippet and ask for the solution in comments.
    5. NO fluff. NO translation errors. NO non-English/non-Arabic characters.
    """

    # استخدام Llama 3.3 70B عبر Groq لضمان الجودة واللغة
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a Senior Engineer who hates filler words. You provide raw, high-level engineering facts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

def run_mission():
    # التأكد من وجود ملف القاعدة
    if not os.path.exists("database.json"):
        with open("database.json", "w") as f:
            json.dump({"history": []}, f)

    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    content = get_ai_content(db["history"])
    
    if content:
        # التوقيع (English Only)
        watermark = "\n\n━━━━━━━━━━━━━━\n🚀 **CodeBilArabi**"
        final_post = content + watermark
        
        # إرسال لتليجرام
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        res = requests.post(url, data={
            "chat_id": CHAT_ID, 
            "text": final_post, 
            "parse_mode": "Markdown"
        })
        
        if res.status_code == 200:
            # حفظ أول سطرين لضمان عدم التكرار
            lines = content.split('\n')
            db["history"].append(" - ".join([line.strip() for line in lines[:2] if line.strip()]))
            with open("database.json", "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
        else:
            print(f"Telegram Error: {res.text}")
    else:
        print("Failed to get content from AI.")

if __name__ == "__main__":
    run_mission()
