import os
import json
import requests
import random

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    # إضافة قسم "The Elite Arena" للتحديات الصعبة
    structure = {
        "System Design & Architecture": [
            "Microservices Patterns (Saga, CQRS, Event Sourcing)",
            "Scalability (Vertical vs Horizontal, Sharding, Replication)",
            "High Availability (Failover strategies, Disaster Recovery)"
        ],
        "Deep Dive Internals": [
            "OS Kernels (Process Scheduling, System Calls, IPC)",
            "Memory Management (Heap vs Stack, Garbage Collection algorithms)",
            "Concurrency (Deadlocks, Livelocks, Race Conditions, Mutex/Semaphores)"
        ],
        "The Elite Arena (Challenges)": [
            "Logic Bug: Find the hidden race condition in this code.",
            "Memory Leak: Identify why this pointer management fails.",
            "Optimization: Refactor this O(n^2) logic into O(log n).",
            "Output Quiz: Predict the output of this complex JS/Python closure."
        ],
        "Network & Security": [
            "Transport Protocols (TCP Congestion Control, QUIC)",
            "Network Security (TLS Handshake, Zero Trust Architecture)"
        ]
    }
    
    main_cat = random.choice(list(structure.keys()))
    sub_topic = random.choice(structure[main_cat])
    
    # برومبت متخصص بيجبر الـ AI إنه يعمل تحدي "Senior Level"
    prompt = f"""
    Act as a Senior Software Architect and Interviewer. 
    Main Category: {main_cat}
    Specific Branch: {sub_topic}
    Previous History: {history[-10:]}

    TASK: 
    - If Category is 'The Elite Arena', provide a TRICKY code snippet and ask the audience to find the bug or predict the output.
    - If other category, provide a high-level technical briefing.
    
    STRICT RULES:
    1. The challenge must be VERY HARD. No basic syntax errors. Focus on Logic, Concurrency, or Memory.
    2. Language: Technical Arabic (Arabic sentences + English technical terms).
    3. Structure:
       Line 1: [{main_cat} | {sub_topic}]
       Line 2: **Challenge Title** or **Technical Title**
       Next Lines: The code snippet or the engineering facts.
    4. End with a call to action: "اكتب الحل في التعليقات" (Only if it's a challenge).
    5. NO introductions. NO filler words.
    """

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a specialized engineer. You hate basic info and love challenging other experts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8 # رفع الحرارة قليلاً لزيادة إبداع التحديات
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error: {e}")
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
        # تم إزالة parse_mode لو كان فيه أكواد معقدة بتبوظ الـ Markdown، أو ممكن تخليها Markdown لو ضامن الـ AI
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": final_post, "parse_mode": "Markdown"})
        
        if res.status_code == 200:
            lines = content.split('\n')
            db["history"].append(" - ".join([line.strip() for line in lines[:2] if line.strip()]))
            with open("database.json", "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
