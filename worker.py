import sys
import os
import logging
from rq import Worker, Connection
from rq.job import Job
from task_queue import redis_client, task_queue
from termcolor import colored

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        print(colored("[+] Starting RQ Worker...", "blue"))
        
        redis_client.ping()
        print(colored("[+] Redis connection successful", "green"))
        
        with Connection(redis_client):
            worker = Worker([task_queue], connection=redis_client)
            print(colored(f"[+] Worker started - Queue: {task_queue.name}", "green"))
            print(colored("[+] Waiting for jobs to be processed...", "yellow"))
            
            worker.work(with_scheduler=True)
            
    except KeyboardInterrupt:
        print(colored("\n[-] Worker stopped", "yellow"))
        sys.exit(0)
    except Exception as e:
        print(colored(f"[-] Worker error: {e}", "red"))
        logger.error(f"Worker error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()