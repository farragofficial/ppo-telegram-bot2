import time
import requests
import base64
import json

# ===== إعدادات البوت =====
TELEGRAM_TOKEN = "8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ"
# استخدمنا الـ WS URL والـ Token الخاص بالـ Railway Browserless
BROWSERLESS_WS_URL = "wss://browserless-production-ffc6.up.railway.app?token=AGs1hzksA1FBUp4WMgNDIq8HVltYPAiamRXEMKffvkFByTkg"
BASE_TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
TARGET_PAGE = "https://ppo.gov.eg/ppo/r/ppoportal/ppoportal/home"
DATA_FILE = "ppo_data.json"

# تحميل البيانات السابقة أو إنشاء جديد
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
except:
    saved_data = {}

# حالة المستخدمين
user_pending = {}      # chat_id -> بيانات مؤقتة
user_save_pending = {} # chat_id -> بيانات جاهزة للحفظ

# ===== دوال Telegram =====
def send_message(chat_id, text):
    requests.post(BASE_TELEGRAM_URL + "sendMessage", data={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo_bytes, filename="page.png"):
    files = {"photo": (filename, photo_bytes)}
    requests.post(BASE_TELEGRAM_URL + "sendPhoto", data={"chat_id": chat_id}, files=files)

# ===== Browserless Puppeteer =====
def take_screenshot_browserless(plate_number, letters, national_id, phone):
    """
    أخذ screenshot كامل للصفحة بعد ملء البيانات على Browserless (Railway)
    """
    js_code = f"""
    async () => {{
        const puppeteer = require('puppeteer-core');
        const browser = await puppeteer.connect({{
            browserWSEndpoint: '{BROWSERLESS_WS_URL}'
        }});
        const page = await browser.newPage();
        await page.goto('{TARGET_PAGE}', {{waitUntil: 'networkidle2'}});
        // إدخال البيانات
        await page.type('#P14_NUMBER_WITH_LETTER', '{plate_number}');
        await page.type('#P14_LETER_1', '{letters[0]}');
        await page.type('#P14_LETER_2', '{letters[1]}');
        await page.type('#P14_LETER_3', '{letters[2]}');
        await page.type('#P7_NATIONAL_ID_CASE_1', '{national_id}');
        await page.type('#P7_PHONE_NUMBER_ID_CASE_1', '{phone}');
        await page.click('#GET_FIN_LETTER_NUMBERS_BTN');
        await page.waitForTimeout(1500);
        try {{ await page.click('#B1776099686727570788'); }} catch{{}}
        await page.waitForTimeout(2000);
        const screenshot = await page.screenshot({{fullPage: true}});
        await browser.close();
        return screenshot.toString('base64');
    }}
    """
    response = requests.post(
        "https://browserless-production-ffc6.up.railway.app/content",
        json={"code": js_code},
        timeout=120
    )
    response.raise_for_status()
    return base64.b64decode(response.json())

# ===== معالجة رسائل المستخدم =====
def process_message(chat_id, text):
    text = text.strip()
    if chat_id not in user_pending and chat_id not in user_save_pending:
        if not text.isdigit():
            send_message(chat_id, "رقم العربية يجب أن يحتوي أرقام فقط. أرسل الرقم مرة أخرى:")
            return
        user_pending[chat_id] = {"step": 1, "plate_number": text}
        send_message(chat_id, "ابعت الحروف الثلاثة:")
        return

    step = user_pending[chat_id]["step"]
    if step == 1:
        letters = text.replace(" ", "").upper()
        if len(letters) != 3:
            send_message(chat_id, "الحروف الثلاثة يجب أن تكون 3 أحرف فقط. ابعتها مرة أخرى:")
            return
        user_pending[chat_id]["letters"] = letters
        user_pending[chat_id]["step"] = 2
        send_message(chat_id, "ابعت الرقم القومي:")
        return
    if step == 2:
        user_pending[chat_id]["national_id"] = text
        user_pending[chat_id]["step"] = 3
        send_message(chat_id, "ابعت رقم الهاتف:")
        return
    if step == 3:
        user_pending[chat_id]["phone"] = text
        send_message(chat_id, "جاري فتح الصفحة وأخذ Screenshot...")
        data = user_pending[chat_id]
        try:
            img_bytes = take_screenshot_browserless(
                data["plate_number"], data["letters"], data["national_id"], data["phone"]
            )
            send_photo(chat_id, img_bytes, filename=f"{data['plate_number']}.png")
            user_save_pending[chat_id] = data.copy()
            send_message(chat_id, "هل تريد حفظ البيانات للوحة؟ (نعم/لا)")
        except Exception as e:
            send_message(chat_id, f"حصل خطأ أثناء العملية: {e}")
        return

    if chat_id in user_save_pending:
        if text.lower() == "نعم":
            data = user_save_pending[chat_id]
            saved_data[data["plate_number"]] = data
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(saved_data, f, ensure_ascii=False, indent=4)
            send_message(chat_id, f"تم حفظ البيانات للوحة: {data['plate_number']}")
        else:
            send_message(chat_id, "تم تجاهل حفظ البيانات.")
        user_save_pending.pop(chat_id, None)
        user_pending.pop(chat_id, None)
        return

# ===== تشغيل البوت بالPolling =====
def main():
    offset = 0
    print("Bot polling started...")
    while True:
        try:
            r = requests.get(BASE_TELEGRAM_URL + "getUpdates", params={"offset": offset, "timeout": 60}, timeout=65).json()
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                process_message(update["message"]["chat"]["id"], update["message"].get("text", ""))
        except Exception as e:
            print("Polling error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
