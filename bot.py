import sys
import time
import logging
import threading
from termcolor import colored
import telebot
from decouple import config
from task_queue import enqueue_ai_request, get_job_status, get_queue_stats, clear_finished_jobs

class TelegramBot:
    def __init__(self):
        self.API_TOKEN = config("API_TOKEN", cast=str)
        self.bot = telebot.TeleBot(self.API_TOKEN)
        
        self.active_jobs = {}
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.register_handlers()
        
        self.start_job_monitor()

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            welcome_text = """
🤖 *Welcome to AI Chat Bot!*

This bot answers your questions using the Ollama AI model.

📋 *Commands:*
• `/start` - Start the bot
• `/help` - Help message
• `/stats` - Queue statistics
• `/model` - Model information
• `/clear` - Clear completed jobs

💬 *Usage:*
Type any question and wait for the AI response!
            """
            self.bot.reply_to(message, welcome_text, parse_mode='Markdown')

        @self.bot.message_handler(commands=['help'])
        def send_help(message):
            help_text = """
🆘 *Help*

This bot answers your questions using the AI model.

🔄 *Process:*
1. Type your question
2. Your request is enqueued
3. The AI model generates the response
4. The response is sent to you

⏱️ *Wait Times:*
• Normal: 5-30 seconds
• Busy times: 1-3 minutes

❓ *Having issues?* Try again or check the status with `/stats`.
            """
            self.bot.reply_to(message, help_text, parse_mode='Markdown')

        @self.bot.message_handler(commands=['stats'])
        def send_stats(message):
            try:
                stats = get_queue_stats()
                stats_text = f"""
📊 *Queue Statistics*

🔄 Pending jobs: {stats.get('queue_length', 0)}
✅ Completed jobs: {stats.get('finished_jobs', 0)}
❌ Failed jobs: {stats.get('failed_jobs', 0)}
🏃 Running jobs: {stats.get('started_jobs', 0)}
⏸️ Deferred jobs: {stats.get('deferred_jobs', 0)}

👤 Active user jobs: {len(self.active_jobs)}
                """
                self.bot.reply_to(message, stats_text, parse_mode='Markdown')
            except Exception as e:
                self.bot.reply_to(message, f"Error getting statistics: {str(e)}")

        @self.bot.message_handler(commands=['model'])
        def send_model_info(message):
            try:
                from ai_service import OllamaService
                ai_service = OllamaService()
                model_info = ai_service.get_model_info()
                
                if model_info['success']:
                    info_text = f"""
🧠 *AI Model Information*

📝 Model: `{model_info['model']}`
👥 Parameters: {model_info['parameters']}
📏 Size: {model_info['size']}
🏷️ Family: {model_info['family']}
                    """
                else:
                    info_text = f"❌ Could not retrieve model information: {model_info.get('error', 'Unknown error')}"
                
                self.bot.reply_to(message, info_text, parse_mode='Markdown')
            except Exception as e:
                self.bot.reply_to(message, f"Error getting model information: {str(e)}")

        @self.bot.message_handler(commands=['clear'])
        def clear_jobs(message):
            try:
                clear_finished_jobs()
                self.bot.reply_to(message, "✅ Completed jobs cleared!")
            except Exception as e:
                self.bot.reply_to(message, f"❌ Job clearing error: {str(e)}")

        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message):
            user_id = message.from_user.id
            message_text = message.text
            
            try:
                if user_id in self.active_jobs:
                    self.bot.reply_to(
                        message, 
                        "⏳ Your previous question is still being processed. Please wait..."
                    )
                    return
                
                processing_msg = self.bot.reply_to(
                    message, 
                    "🤔 Thinking... Please wait."
                )
                
                job_id = enqueue_ai_request(user_id, message_text)
                
                self.active_jobs[user_id] = {
                    'job_id': job_id,
                    'message_id': message.message_id,
                    'processing_msg_id': processing_msg.message_id,
                    'chat_id': message.chat.id,
                    'start_time': time.time()
                }
                
                self.logger.info(f"AI request enqueued for user {user_id}: {job_id}")
                
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")
                self.bot.reply_to(
                    message, 
                    "❌ An error occurred. Please try again."
                )

    def start_job_monitor(self):
        def monitor_jobs():
            while True:
                try:
                    completed_jobs = []
                    
                    for user_id, job_info in self.active_jobs.items():
                        job_id = job_info['job_id']
                        status = get_job_status(job_id)
                        
                        if status['status'] == 'finished' and 'result' in status:
                            result = status['result']
                            self.handle_job_completion(user_id, job_info, result)
                            completed_jobs.append(user_id)
                            
                        elif status['status'] == 'failed':
                            error_msg = status.get('error', 'Unknown error')
                            self.handle_job_failure(user_id, job_info, error_msg)
                            completed_jobs.append(user_id)
                            
                        elif time.time() - job_info['start_time'] > 300:
                            self.handle_job_timeout(user_id, job_info)
                            completed_jobs.append(user_id)
                    
                    for user_id in completed_jobs:
                        if user_id in self.active_jobs:
                            del self.active_jobs[user_id]
                    
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Job monitoring error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_jobs, daemon=True)
        monitor_thread.start()

    def handle_job_completion(self, user_id, job_info, result):
        try:
            chat_id = job_info['chat_id']
            processing_msg_id = job_info['processing_msg_id']
            
            try:
                self.bot.delete_message(chat_id, processing_msg_id)
            except:
                pass
            
            if result['success']:
                response_text = result['response']
                
                if len(response_text) > 4096:
                    for i in range(0, len(response_text), 4096):
                        self.bot.send_message(chat_id, response_text[i:i+4096])
                else:
                    self.bot.send_message(chat_id, response_text)
                
                self.logger.info(f"AI response sent for user {user_id}")
            else:
                error_response = result.get('response', 'An error occurred.')
                self.bot.send_message(chat_id, f"❌ {error_response}")
                
        except Exception as e:
            self.logger.error(f"Job completion handling error: {e}")

    def handle_job_failure(self, user_id, job_info, error_msg):
        try:
            chat_id = job_info['chat_id']
            processing_msg_id = job_info['processing_msg_id']
            
            try:
                self.bot.delete_message(chat_id, processing_msg_id)
            except:
                pass
            
            self.bot.send_message(
                chat_id, 
                "❌ Your request failed. Please try again."
            )
            
            self.logger.error(f"Job failed for user {user_id}: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"Job failure handling error: {e}")

    def handle_job_timeout(self, user_id, job_info):
        try:
            chat_id = job_info['chat_id']
            processing_msg_id = job_info['processing_msg_id']
            
            try:
                self.bot.delete_message(chat_id, processing_msg_id)
            except:
                pass
            
            self.bot.send_message(
                chat_id, 
                "⏰ Your request timed out. Please try again."
            )
            
            self.logger.warning(f"Job timed out for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Job timeout handling error: {e}")

    def run(self):
        try:
            print(colored("[+] Starting bot...", "blue"))
            
            try:
                from ai_service import OllamaService
                ai_service = OllamaService()
                if not ai_service.ensure_model_ready():
                    print(colored("[-] AI model not ready, but bot is starting...", "yellow"))
                else:
                    print(colored("[+] AI model ready", "green"))
            except Exception as e:
                print(colored(f"[-] AI service check failed, but bot is starting: {e}", "yellow"))
                
            print(colored("[+] Bot started and running...", "green"))
            
            self.bot.polling(none_stop=True, interval=0, timeout=20)
            
        except KeyboardInterrupt:
            print(colored("\n[-] Bot stopped", "yellow"))
        except Exception as e:
            self.logger.error(f"Bot error: {e}")
            print(colored(f"[-] Bot error: {e}", "red"))

if __name__ == "__main__":
    bot_instance = TelegramBot()
    bot_instance.run()