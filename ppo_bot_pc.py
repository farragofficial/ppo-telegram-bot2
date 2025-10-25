import time
import json
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from playwright.sync_api import sync_playwright

# ===== إعدادات البوت =====
TELEGRAM_TOKEN = '8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ'  # ضع توكن البوت هنا مباشرة
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

# ===== Telegram Handlers =====
PLATE, LETTERS, NID, PHONE, SAVE = range(5)

def start(update, context):
    update.message.reply_text("أرسل رقم العربية لتبدأ العملية (أرقام فقط):")
    return PLATE

def handle_plate(update, context):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("رقم العربية يجب أن يحتوي أرقام فقط. أرسل الرقم مرة أخرى:")
        return PLATE
    context.user_data['plate_number'] = text
    if text in saved_data:
        context.user_data.update(saved_data[text])
        update.message.reply_text(f"اللوحة {text} محفوظة مسبقًا. جاري جلب المخالفات...")
        return fetch_violations(update, context)
    update.message.reply_text("ابعت الحروف الثلاثة:")
    return LETTERS

def handle_letters(update, context):
    letters = update.message.text.strip().replace(" ", "").upper()
    if len(letters) != 3:
        update.message.reply_text("الحروف الثلاثة يجب أن تكون 3 أحرف فقط. ابعتها مرة أخرى:")
        return LETTERS
    context.user_data['letters'] = letters
    update.message.reply_text("ابعت الرقم القومي:")
    return NID

def handle_nid(update, context):
    context.user_data['national_id'] = update.message.text.strip()
    update.message.reply_text("ابعت رقم الهاتف:")
    return PHONE

def handle_phone(update, context):
    context.user_data['phone'] = update.message.text.strip()
    update.message.reply_text("جاري فتح الموقع وجلب المخالفات...")
    return fetch_violations(update, context)

def fetch_violations(update, context):
    data = context.user_data
    try:
        p, browser, page = make_driver()
        open_page(page)
        fill_data(page, data['plate_number'], data['letters'], data['national_id'], data['phone'])
        table = get_violations_table(page)
        if table:
            update.message.reply_text(format_table(table))
        else:
            update.message.reply_text("لم يتم العثور على مخالفات.")
        browser.close()
        p.stop()
        user_save_pending[update.message.chat_id] = data.copy()
        update.message.reply_text("هل تريد حفظ البيانات للوحة؟ (نعم/لا)")
        return SAVE
    except Exception as e:
        update.message.reply_text(f"حصل خطأ: {e}")
        return ConversationHandler.END

def handle_save(update, context):
    text = update.message.text.strip().lower()
    chat_id = update.message.chat_id
    if text == "نعم":
        data = user_save_pending.get(chat_id)
        if data:
            saved_data[data['plate_number']] = data
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(saved_data, f, ensure_ascii=False, indent=4)
            update.message.reply_text(f"تم حفظ البيانات للوحة: {data['plate_number']}")
    else:
        update.message.reply_text("تم تجاهل حفظ البيانات.")
    user_save_pending.pop(chat_id, None)
    return ConversationHandler.END

def cancel(update, context):
    update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# ===== تشغيل البوت =====
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PLATE: [MessageHandler(Filters.text & ~Filters.command, handle_plate)],
            LETTERS: [MessageHandler(Filters.text & ~Filters.command, handle_letters)],
            NID: [MessageHandler(Filters.text & ~Filters.command, handle_nid)],
            PHONE: [MessageHandler(Filters.text & ~Filters.command, handle_phone)],
            SAVE: [MessageHandler(Filters.text & ~Filters.command, handle_save)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
