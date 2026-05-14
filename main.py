import os
import json
import requests

# استدعاء المفاتيح من خزنة الـ Secrets
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    recent_history = history[-50:]
    
    prompt = f"""
    أنت الآن "Senior Software Engineer" والمحرر التقني لمبادرة CodeBilArabi.
    هدفك: تقديم محتوى تقني "ثقيل" وعميق للمحترفين فقط.
    المواضيع السابقة (تجنب التكرار): {recent_history}

    اختر واحداً من هذه المسارات التقنية عشوائياً:
    1. [System Design]: شرح نمط معماري متقدم أو حل لمشكلة Scalability.
    2. [Deep Dive]: الغوص في كواليس عمل اللغات (مثل Garbage Collection, JIT, Concurrency).
    3. [Logic Bug Challenge]: اكتب قطعة كود (Snippet) تحتوي على خطأ منطقي (Logic Bug) "صعب جداً" وغير ظاهر للعين المجردة، واطلب من المتابعين اكتشافه في التعليقات.
    4. [Complete The Code]: اكتب قطعة كود متقدمة ناقصة جزءاً جوهرياً (مثل Function معينة أو Regex معقد) واطلب من المتابعين تكملة الكود في التعليقات.
    5. [DevOps & Tools]: أداة CLI متطورة أو تقنية Automation ترفع الإنتاجية.
    6. [Security & Logic]: ثغرة برمجية منطقية أو مفهوم تشفير متقدم.

    القواعد الصارمة:
    - اللغة: عربية تقنية رصينة (المصطلحات التقنية تظل بالإنجليزية).
    - الهيكل:
        السطر الأول: [اسم المسار]
        السطر الثاني: **العنوان التقني**
        التفاصيل: شرح مركز أو قطعة الكود المطلوبة.
    - التحديات (Challenge) يجب أن تكون صعبة جداً وتستهدف ذكاء المبرمجين.
    - ممنوع تماماً أي مقدمات، نهايات، أو كلمات "هابطة".
    - المحتوى موجه لمن لديهم خبرة سنوات.
    """

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8 # لزيادة الإبداع في التحديات والأخطاء
            },
            timeout=30
        )
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        return response.json()['choices'][0]['message']['content'].strip()

def run_mission():
    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    raw_content = get_ai_content(db["history"])
    
    # التوقيع الرسمي
    watermark = "\n\n━━━━━━━━━━━━━━\n🚀 **CodeBilArabi**"
    final_post = raw_content + watermark
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID, 
        "text": final_post,
        "parse_mode": "Markdown"
    })
    
    # حفظ المسار والعنوان لضمان عدم التكرار
    lines = raw_content.split('\n')
    full_title = " - ".join([line.strip() for line in lines[:2] if line.strip()])
    db["history"].append(full_title)
    
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
