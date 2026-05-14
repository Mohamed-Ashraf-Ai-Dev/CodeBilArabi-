import os
import json
import requests

# استدعاء المفاتيح من خزنة الـ Secrets
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    # ميزة الـ Slicing: إرسال آخر 50 عنوان فقط
    recent_history = history[-50:]
    
    # برومبت صارم لمنع النهايات والمقدمات
    prompt = f"""
    أنت الآن "كبير مهندسي البرمجيات" لمبادرة CodeBilArabi.
    هدفك: تقديم زتونة تقنية عميقة ومختصرة جداً.
    المواضيع السابقة لتجنب التكرار: {recent_history}

    اختر عشوائياً واحداً من القوالب التالية:
    1. [نصيحة من الكواليس]: سر برمجى احترافي.
    2. [زتونة اللغات]: معلومة عميقة (Deep Dive) في لغة برمجة.
    3. [لغز الكود]: كود صغير بمنطق خفي مع سؤال "ما النتيجة؟".
    4. [مقارنة العمالقة]: فرق جوهري بين تقنيتين.
    5. [أدوات المحترفين]: أداة CLI أو مكتبة GitHub قوية.
    6. [فلسفة المنطق]: ربط مفهوم منطقي بطريقة عمل الحاسوب.

    الشروط الصارمة:
    - ابدأ بـ [نوع البوست] ثم العنوان مباشرة.
    - ممنوع تماماً أي مقدمات أو نهايات أو جمل تفاعلية.
    - البوست ينتهي بانتهاء المعلومة التقنية فقط.
    - اللغة: عربية تقنية قوية بإيقاع "الزتونة" (جمل قصيرة وموزونة).
    """

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Fallback triggered: {e}")
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
    
    # العلامة المائية الاحترافية التي طلبتها
    watermark = "\n\n─── ⋆⋅☆⋅⋆ ───\n🔹 **CodeBilArabi** | كود بالعربي 💻"
    final_post = raw_content + watermark
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID, 
        "text": final_post,
        "parse_mode": "Markdown"
    })
    
    title = raw_content.split('\n')[0]
    db["history"].append(title)
    
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
