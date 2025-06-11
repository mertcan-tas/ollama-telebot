from termcolor import colored
import telebot
from decouple import config

class TelegramBot:
    def __init__(self):
        self.API_TOKEN = config("API_TOKEN", cast=str)
        self.bot = telebot.TeleBot(self.API_TOKEN)
        self.register_handlers()

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            self.bot.reply_to(message, "Hello! I am your bot.")
    
    def run(self):
        try:
            print(colored("[+] Bot Started", "blue"))
            self.bot.polling()
        except Exception as e:
            print(colored(f"[-] Error: {e}", "red"))

if __name__ == "__main__":
    bot_instance = TelegramBot()
    bot_instance.run()