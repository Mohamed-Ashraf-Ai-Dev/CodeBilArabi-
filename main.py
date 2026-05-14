import os
import json
import requests
import random

# استدعاء المفاتيح من خزنة الـ Secrets
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    recent_history = history[-50:]
    
    # مصفوفة المسارات لضمان الاختيار العشوائي الحقيقي من طرف الكود وليس الـ AI
    categories = [
        {"name": "System Design", "desc": "شرح معماري متقدم لـ Microservices أو Distributed Systems."},
        {"name": "Deep Dive", "desc": "تحليل تقني لنواة أنظمة التشغيل أو مترجمات اللغات (Compilers)."},
        {"name": "Logic Bug Challenge", "desc": "كود برمجي خبيث به Logic Error لا يكتشفه إلا خبير، مع طلب الحل."},
        {"name": "Complete The Code", "desc": "تحدي إكمال دالة (Function) تتعامل مع Async أو Memory Management."},
        {"name": "DevOps Architecture", "desc": "هيكلة CI/CD Pipelines أو Kubernetes Networking."},
        {"name": "Security Internals", "desc": "تحليل لثغرات الـ Buffer Overflow أو الـ Logic Flaws في الـ Auth."}
    ]
    
    selected = random.choice(categories)
    
    # برومبت صارم جداً يمنع الرغي واللغة الضعيفة
    prompt = f"""
    You are a Elite Software Architect. Write a technical post for CodeBilArabi.
    Target Audience: Senior Developers only.
    Category: {selected['name']} ({selected['desc']})
    History to avoid: {recent_history}

    Strict Instructions:
    1. Language: Heavy Technical Arabic (Keep English terms as is).
    2. Format:
       Line 1: [{selected['name']}]
       Line 2: **Technical Title**
       Details: Use bullet points. Explain "Behind the scenes" logic.
    3. NO "Deep Dive" into Garbage Collection (Already done).
    4. NO introductions ("In this post...", "Hello").
    5. NO conclusions.
    6. If it's a Challenge: Provide the code and ask for the fix/completion in the comments.
    7. Be concise, aggressive, and highly technical.
    """

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "system", "content": "You are a Senior Engineer who hates fluff and talks only in deep technical facts."},
                     {"role": "user", "content": prompt}],
        "temperature": 0.9 # رفع درجة الإبداع لمنع التكرار
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        # البديل في حال الفشل
        headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers_groq, 
                                 json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()

def run_mission():
    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    raw_content = get_ai_content(db["history"])
    
    # التوقيع الرسمي النهائي
    watermark = "\n\n━━━━━━━━━━━━━━\n🚀 **CodeBilArabi**"
    final_post = raw_content + watermark
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": final_post, "parse_mode": "Markdown"})
    
    # حفظ أول سطرين في الذاكرة
    lines = raw_content.split('\n')
    full_title = " - ".join([line.strip() for line in lines[:2] if line.strip()])
    db["history"].append(full_title)
    
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
