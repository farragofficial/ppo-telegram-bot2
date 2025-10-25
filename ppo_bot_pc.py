import asyncio
import os
import tempfile
from telebot import TeleBot
from playwright.async_api import async_playwright

# 🔹 توكن البوت
TOKEN = os.environ.get("BOT_TOKEN", "8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ")
bot = TeleBot(TOKEN)

async def generate_pdf_bytes(url: str) -> bytes:
    """يفتح الموقع المطلوب ويعيد ملف PDF كـ bytes"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        pdf_bytes = await page.pdf(format="A4", print_background=True)
        await browser.close()
        return pdf_bytes

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "👋 أهلاً بيك! من فضلك ابعت رقم العربية:")
    bot.register_next_step_handler(message, handle_plate)

def handle_plate(message):
    chat_id = message.chat.id
    plate = message.text.strip()
    bot.send_message(chat_id, f"🔍 جاري تجهيز التقرير لـ {plate}...")

    async def process():
        try:
            # 🔹 هنا ممكن نغير الرابط حسب الرقم لو الموقع بيتطلبه
            url = "https://ppo.gov.eg/ppo/r/ppoportal/ppoportal/home"
            pdf_data = await generate_pdf_bytes(url)

            # 🔹 نحفظ مؤقتًا عشان نقدر نبعت
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_data)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                bot.send_document(chat_id, f, caption=f"📄 تم إنشاء ملف PDF خاص بـ {plate} ✅")

            os.remove(tmp_path)
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ حصل خطأ أثناء إنشاء الملف:\n{e}")

    asyncio.run(process())

if __name__ == "__main__":
    print("🤖 Bot started on Render...")
    bot.infinity_polling(timeout=60)
