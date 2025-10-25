import asyncio
import tempfile
import subprocess
import sys
from telebot import TeleBot, types

# توكن البوت
BOT_TOKEN = "8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ"

bot = TeleBot(BOT_TOKEN)

# ======================================================
# تأكد من تثبيت playwright والمتصفح
# ======================================================
import subprocess, sys, os

# ======================================================
# تأكد من تثبيت playwright والمتصفح
# ======================================================
try:
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])

# ✅ تحميل المتصفح دائماً قبل التشغيل
subprocess.call([sys.executable, "-m", "playwright", "install", "chromium"])
from playwright.async_api import async_playwright


# ======================================================
# دالة لتحويل موقع إلى PDF
# ======================================================
async def generate_pdf_from_url(url: str) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ],
        )
        page = await browser.new_page()
        await page.goto(url, wait_until="load", timeout=60000)
        pdf_bytes = await page.pdf(format="A4")
        await browser.close()
        return pdf_bytes

# ======================================================
# تفاعل البوت
# ======================================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 أهلاً بيك! ابعت رقم العربية عشان أجيبلك الملف PDF.")

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    car_number = message.text.strip()
    bot.reply_to(message, f"⏳ جاري إنشاء ملف PDF لرقم العربية: {car_number}...")
    asyncio.run(process_request(message, car_number))

async def process_request(message, car_number):
    try:
        # مثال: فتح صفحة PPO
        url = f"https://ppo.gov.eg/ppo/r/ppoportal/ppoportal/home?plate={car_number}"

        pdf_bytes = await generate_pdf_from_url(url)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as pdf:
            bot.send_document(message.chat.id, pdf, visible_file_name=f"{car_number}.pdf")

    except Exception as e:
        bot.reply_to(message, f"⚠️ حصل خطأ أثناء إنشاء الملف:\n{e}")

# ======================================================
# تشغيل البوت
# ======================================================
print("🤖 Bot started successfully on Render/KataBump...")
bot.infinity_polling()


