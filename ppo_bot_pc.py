import time
import json
import requests
from playwright.sync_api import sync_playwright

# ===== إعدادات البوت =====
TELEGRAM_TOKEN = '8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ'  # ضع التوكن هنا مباشرة
DATA_FILE = "ppo_data.json"

# تحميل البيانات السابقة أو إنشاء جديد
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
except:
    saved_data = {}

# حالة المستخدمين
user_pending = {}  # chat_id -> بيانات مؤقتة
user_save_pending = {}  # chat_id -> بيانات جاهزة للحفظ

# رابط Telegram API
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"

# ===== Playwright =====
TARGET_URL = "https://ppo.gov.eg/ppo/r/ppoportal/ppoportal/home"

def make_driver():
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    return p, browser, page

def open_page(page):
    page.goto(TARGET_URL)
    time.sleep(2)
    try:
        divs = page.query_selector_all(".icon-title h5")
        for h5 in divs:
            if "نيابات المرور" in h5.inner_text():
                h5.click()
                break
        time.sleep(1)
    except:
        pass

def fill_data(page, plate_number, letters, national_id, phone):
    page.fill("input#P14_NUMBER_WITH_LETTER", plate_number)
    for i, letter in enumerate(letters[:3], start=1):
        page.fill(f"#P14_LETER_{i}", letter)
    page.fill("input#P7_NATIONAL_ID_CASE_1", national_id)
    page.fill("input#P7_PHONE_NUMBER_ID_CASE_1", phone)
    page.click("#GET_FIN_LETTER_NUMBERS_BTN")
    time.sleep(1.5)
    try:
        page.click("#B1776099686727570788")
    except:
        buttons = page.query_selector_all("button")
        for b in buttons:
            if "تفاصيل" in b.inner_text():
                b.click()
                break
    time.sleep(2)

def get_violations_table(page):
    try:
        table = page.query_selector("#report_table_R1785299912873701447")
        if not table:
            return []
        rows = table.query_selector_all("tr")
        data = []
        for row in rows:
            cols = row.query_selector_all("td")
            row_data = [c.inner_text().strip() for c in cols if c.inner_text().strip()]
            if row_data:
                data.append(row_data)
        return data
    except:
        return []

def format_table(data):
    lines = []
    for i, row in enumerate(data, start=1):
        lines.append(f"{i}. " + " | ".join(row))
    return "\n".join(lines)

def send_telegram(chat_id, text):
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, data=payload)

# ===== التفاعل مع المستخدم =====
def process_message(chat_id, text):
    text = text.strip()
    # مرحلة البداية
    if chat_id not in user_pending and chat_id not in user_save_pending:
        if not text.isdigit():
            send_telegram(chat_id, "رقم العربية يجب أن يحتوي أرقام فقط. أرسل الرقم مرة أخرى:")
            return
        user_pending[chat_id] = {"step": 1, "plate_number": text}
        send_telegram(chat_id, "ابعت الحروف الثلاثة:")
        return

    step = user_pending[chat_id]["step"]
    if step == 1:
        letters = text.replace(" ", "").upper()
        if len(letters) != 3:
            send_telegram(chat_id, "الحروف الثلاثة يجب أن تكون 3 أحرف فقط. ابعتها مرة أخرى:")
            return
        user_pending[chat_id]["letters"] = letters
        user_pending[chat_id]["step"] = 2
        send_telegram(chat_id, "ابعت الرقم القومي:")
        return
    if step == 2:
        user_pending[chat_id]["national_id"] = text
        user_pending[chat_id]["step"] = 3
        send_telegram(chat_id, "ابعت رقم الهاتف:")
        return
    if step == 3:
        user_pending[chat_id]["phone"] = text
        send_telegram(chat_id, "جاري فتح الموقع وجلب المخالفات...")
        # تشغيل Playwright وجلب الجدول
        data = user_pending[chat_id]
        try:
            p, browser, page = make_driver()
            open_page(page)
            fill_data(page, data["plate_number"], data["letters"], data["national_id"], data["phone"])
            table = get_violations_table(page)
            if table:
                send_telegram(chat_id, format_table(table))
            else:
                send_telegram(chat_id, "لم يتم العثور على مخالفات.")
            browser.close()
            p.stop()
            user_save_pending[chat_id] = data.copy()
            send_telegram(chat_id, "هل تريد حفظ البيانات للوحة؟ (نعم/لا)")
        except Exception as e:
            send_telegram(chat_id, f"حصل خطأ: {e}")
        return

    # مرحلة حفظ البيانات
    if chat_id in user_save_pending:
        if text.lower() == "نعم":
            data = user_save_pending[chat_id]
            saved_data[data["plate_number"]] = data
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(saved_data, f, ensure_ascii=False, indent=4)
            send_telegram(chat_id, f"تم حفظ البيانات للوحة: {data['plate_number']}")
        else:
            send_telegram(chat_id, "تم تجاهل حفظ البيانات.")
        user_save_pending.pop(chat_id, None)
        user_pending.pop(chat_id, None)
        return

# ===== تشغيل البوت (polling بسيط) =====
def main():
    offset = 0
    while True:
        url = f"{BASE_URL}getUpdates?offset={offset}&timeout=60"
        try:
            r = requests.get(url).json()
            for result in r.get("result", []):
                offset = result["update_id"] + 1
                if "message" in result:
                    chat_id = result["message"]["chat"]["id"]
                    text = result["message"].get("text", "")
                    if text:
                        process_message(chat_id, text)
        except Exception as e:
            print("Error:", e)
        time.sleep(1)

if __name__ == "__main__":
    main()
