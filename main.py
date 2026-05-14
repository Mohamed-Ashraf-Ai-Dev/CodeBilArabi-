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
    
    # تصنيفات تقنية عميقة
    categories = [
        "Kernel Internals & Memory Mapping",
        "High-Concurrency & Locking Strategies",
        "Distributed Systems Consensus (Raft/Paxos)",
        "Compiler Optimization Techniques",
        "Network Protocol Engineering (TCP/QUIC)",
        "Advanced Cryptographic Implementation"
    ]
    selected_topic = random.choice(categories)
    
    # برومبت مصمم خصيصاً لنموذج Gemma ليعطي أقصى أداء تقني
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

    # استخدام Gemma 2 27B من خلال OpenRouter
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": "google/gemma-2-27b-it", # تم التغيير إلى Gemma 2
        "messages": [
            {"role": "system", "content": "You are a specialized software architect. You speak only in technical facts and code."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Gemma failed, falling back to Llama: {e}")
        # البديل في حال تعطل Gemma (Llama 3.3 70B)
        headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers_groq, 
                            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, timeout=30)
        return res.json()['choices'][0]['message']['content'].strip()

def run_mission():
    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    raw_content = get_ai_content(db["history"])
    
    # التوقيع الرسمي
    watermark = "\n\n━━━━━━━━━━━━━━\n🚀 **CodeBilArabi**"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": raw_content + watermark, "parse_mode": "Markdown"})
    
    # حفظ التاريخ
    lines = raw_content.split('\n')
    db["history"].append(" - ".join([line.strip() for line in lines[:2] if line.strip()]))
    
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
