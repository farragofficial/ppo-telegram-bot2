import requests
from telebot import TeleBot
import tempfile

BOT_TOKEN = "8343868844:AAG5rK_3MflfqxRiBBe7eM4Ux0iXQvBzjrQ"
bot = TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 أهلاً بيك! ابعت رقم العربية عشان أجيبلك صورة الصفحة كاملة.")

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    car_number = message.text.strip()
    bot.reply_to(message, f"📸 جاري التقاط صورة لرقم العربية: {car_number}...")
    try:
        # الموقع اللي عايز تصوره
        base_url = "https://ppo.gov.eg/ppo/r/ppoportal/ppoportal/home"
        full_url = f"{base_url}?plate={car_number}"

        # API خارجية للسكرينشوت
        screenshot_url = f"https://image.thum.io/get/fullpage/{full_url}"

        # تحميل الصورة
        response = requests.get(screenshot_url, timeout=60)
        response.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(response.content)
        tmp.close()

        # إرسال الصورة للمستخدم
        with open(tmp.name, "rb") as img:
            bot.send_photo(message.chat.id, img, caption=f"📄 الصورة الكاملة للموقع ({car_number})")

    except Exception as e:
        bot.reply_to(message, f"⚠️ حصل خطأ أثناء إنشاء الصورة:\n{e}")

print("🤖 Bot started successfully (Screenshot version)...")
bot.infinity_polling()
