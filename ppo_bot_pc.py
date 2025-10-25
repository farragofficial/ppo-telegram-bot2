import requests
from weasyprint import HTML
from telebot import TeleBot
import tempfile

# توكن البوت
BOT_TOKEN = "8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ"
bot = TeleBot(BOT_TOKEN)

def generate_pdf_from_url(url: str, car_number: str) -> str:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    HTML(string=response.text, base_url=url).write_pdf(tmp.name)
    return tmp.name

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 أهلاً بيك! ابعت رقم العربية عشان أجيبلك الملف PDF.")

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    car_number = message.text.strip()
    bot.reply_to(message, f"⏳ جاري إنشاء ملف PDF لرقم العربية: {car_number}...")
    try:
        base_url = "https://ppo.gov.eg/ppo/r/ppoportal/ppoportal/home"
        pdf_path = generate_pdf_from_url(f"{base_url}?plate={car_number}", car_number)
        with open(pdf_path, "rb") as pdf:
            bot.send_document(message.chat.id, pdf, visible_file_name=f"{car_number}.pdf")
    except Exception as e:
        bot.reply_to(message, f"⚠️ حصل خطأ أثناء إنشاء الملف:\n{e}")

print("🤖 Bot started successfully (WeasyPrint version)...")
bot.infinity_polling()

