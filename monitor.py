import time
import sys
import redis
import requests
from termcolor import colored
from decouple import config
from task_queue import get_queue_stats, redis_client

class SystemMonitor:
    def __init__(self):
        self.redis_host = config("REDIS_HOST", default="localhost")
        self.redis_port = config("REDIS_PORT", default=6379, cast=int)
        self.ollama_host = config("OLLAMA_HOST", default="localhost")
        self.ollama_port = config("OLLAMA_PORT", default=11434, cast=int)
        
    def check_redis(self):
        try:
            redis_client.ping()
            return {"status": "✅", "message": "Redis is running"}
        except Exception as e:
            return {"status": "❌", "message": f"Redis error: {str(e)}"}
    
    def check_ollama(self):
        try:
            response = requests.get(f"http://{self.ollama_host}:{self.ollama_port}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_count = len(models)
                return {"status": "✅", "message": f"Ollama is running ({model_count} models)"}
            else:
                return {"status": "❌", "message": f"Ollama HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "❌", "message": f"Ollama error: {str(e)}"}
    
    def get_system_status(self):
        redis_status = self.check_redis()
        ollama_status = self.check_ollama()
        
        try:
            queue_stats = get_queue_stats()
        except Exception as e:
            queue_stats = {"error": str(e)}
        
        return {
            "redis": redis_status,
            "ollama": ollama_status,
            "queue": queue_stats,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def print_status(self):
        status = self.get_system_status()
        
        print(colored("=" * 60, "blue"))
        print(colored(f"🔍 System Status - {status['timestamp']}", "cyan"))
        print(colored("=" * 60, "blue"))
        
        redis_info = status['redis']
        print(f"Redis: {redis_info['status']} {redis_info['message']}")
        
        ollama_info = status['ollama']
        print(f"Ollama: {ollama_info['status']} {ollama_info['message']}")
        
        queue_info = status['queue']
        if 'error' not in queue_info:
            print(colored("\n📊 Queue Statistics:", "yellow"))
            print(f"  🔄 Pending jobs: {queue_info.get('queue_length', 0)}")
            print(f"  ✅ Completed: {queue_info.get('finished_jobs', 0)}")
            print(f"  ❌ Failed: {queue_info.get('failed_jobs', 0)}")
            print(f"  🏃 Running: {queue_info.get('started_jobs', 0)}")
            print(f"  ⏸️ Deferred: {queue_info.get('deferred_jobs', 0)}")
        else:
            print(f"Queue: ❌ {queue_info['error']}")
        
        print(colored("=" * 60, "blue"))

def main():
    monitor = SystemMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        print(colored("🔍 Continuous monitoring mode (Ctrl+C to exit)", "green"))
        try:
            while True:
                monitor.print_status()
                time.sleep(10)
                print("\n")
        except KeyboardInterrupt:
            print(colored("\n👋 Monitoring stopped", "yellow"))
    else:
        monitor.print_status()

if __name__ == "__main__":
    main()