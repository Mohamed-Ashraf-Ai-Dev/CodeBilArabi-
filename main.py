import os
import json
import requests
import random

# استدعاء المفاتيح
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    recent_history = history[-50:]
    categories = [
        "Kernel Internals & Memory Mapping",
        "High-Concurrency & Locking Strategies",
        "Distributed Systems Consensus (Raft/Paxos)",
        "Compiler Optimization Techniques",
        "Network Protocol Engineering (TCP/QUIC)",
        "Advanced Cryptographic Implementation"
    ]
    selected_topic = random.choice(categories)
    
    prompt = f"""
    You are a Hardcore Systems Engineer. Write a technical post for CodeBilArabi.
    Topic: {selected_topic}
    History: {recent_history}

    STRICT RULES:
    1. Language: Arabic (Technical terms MUST remain in English).
    2. Format:
       [Category]
       **Bold Technical Title**
       - Use bullet points for raw engineering facts.
       - Focus on "How it works under the hood".
    3. If Category is a Challenge: Provide a complex code snippet with a subtle logic flaw.
    4. NO fluff. NO greetings. NO translation errors.
    """

    # استخدام نسخة Gemma 2 المجانية لضمان العمل بدون رصيد
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": "google/gemma-2-9b-it:free", 
        "messages": [
            {"role": "system", "content": "You are a specialized software architect. You speak only in technical facts and code."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        response.raise_for_status() # التأكد إن الطلب نجح
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Primary Model failed: {e}")
        # البديل: Llama 3 عبر Groq (سريع وموثوق جداً)
        try:
            headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers_groq, 
                                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, timeout=30)
            return res.json()['choices'][0]['message']['content'].strip()
        except Exception as e2:
            print(f"Fallback Model also failed: {e2}")
            return None

def run_mission():
    # التأكد من وجود ملف القاعدة لتجنب الـ Crash
    if not os.path.exists("database.json"):
        with open("database.json", "w") as f:
            json.dump({"history": []}, f)

    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    content = get_ai_content(db["history"])
    
    if content:
        watermark = "\n\n━━━━━━━━━━━━━━\n🚀 **CodeBilArabi**"
        final_text = content + watermark
        
        # محاولة الإرسال لتليجرام مع طباعة الرد لمعرفة السبب لو فشل
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        tg_res = requests.post(url, data={
            "chat_id": CHAT_ID, 
            "text": final_text, 
            "parse_mode": "Markdown"
        })
        
        if tg_res.status_code != 200:
            print(f"Telegram Error: {tg_res.text}")
            # لو فشل بسبب الـ Markdown نجرب نبعت نص سادة
            requests.post(url, data={"chat_id": CHAT_ID, "text": final_text})
        
        # حفظ التاريخ (فقط لو تم توليد محتوى)
        lines = content.split('\n')
        db["history"].append(" - ".join([line.strip() for line in lines[:2] if line.strip()]))
        with open("database.json", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    else:
        print("Mission failed: No content generated.")

if __name__ == "__main__":
    run_mission()
