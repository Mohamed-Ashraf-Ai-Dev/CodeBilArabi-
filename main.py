import os
import json
import requests

# استدعاء المفاتيح من خزنة الـ Secrets
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def get_ai_content(history):
    # ميزة الـ Slicing: إرسال آخر 50 عنوان فقط لتوفير المساحة ومنع الأخطاء مستقبلاً
    recent_history = history[-50:]
    
    # البرومبت المطور لضمان محتوى احترافي وغير بديهي
    prompt = f"""
    أنت الآن "كبير مهندسي البرمجيات" لمبادرة CodeBilArabi.
    هدفك: تقديم زتونة تقنية عميقة ومختصرة جداً.
    المواضيع السابقة لتجنب التكرار: {recent_history}

    اختر عشوائياً واحداً من القوالب التالية:
    1. [نصيحة من الكواليس]: سر برمجى في Clean Code أو System Architecture لا يعرفه المبتدئون.
    2. [زتونة اللغات]: معلومة عميقة (Deep Dive) في لغة برمجة (مثل الـ Memory Management أو Event Loop).
    3. [لغز الكود]: كود صغير بمنطق خفي مع سؤال "ما النتيجة؟" وشرح الحل بأسلوب رتمي.
    4. [مقارنة العمالقة]: فرق جوهري بين تقنيتين يختلطان على الناس (مثل JWT vs Sessions) في 4 جمل رنانة.
    5. [أدوات المحترفين]: أداة CLI أو مكتبة GitHub تغير حياة المطور.
    6. [فلسفة المنطق]: ربط مفهوم منطقي فلسفي بطريقة عمل الحاسوب.

    الشروط:
    - ابدأ بـ [نوع البوست] ثم العنوان مباشرة.
    - ممنوع تماماً أي مقدمات (مثل حسناً أو إليك).
    - اللغة: عربية تقنية قوية بإيقاع "الزتونة" (جمل قصيرة وموزونة).
    """

    # المحاولة الأولى: OpenRouter (Gemini 2.0 Flash المجاني)
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
        print(f"OpenRouter fallback triggered due to: {e}")
        # المحاولة الثانية (البديل): Groq (Llama 3.3) لضمان العمل للأبد
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
    # فتح قاعدة البيانات البسيطة
    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    # توليد المحتوى
    post_content = get_ai_content(db["history"])
    
    # النشر على تليجرام
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": post_content})
    
    # تحديث التاريخ بالعنوان فقط (أول سطر) لتوفير المساحة
    title = post_content.split('\n')[0]
    db["history"].append(title)
    
    # حفظ التحديث في الملف
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_mission()
