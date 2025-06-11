import redis
from rq import Queue
from rq.job import Job
from decouple import config
import logging
from typing import Dict, Any
import json

redis_host = config("REDIS_HOST", default="localhost")
redis_port = config("REDIS_PORT", default=6379, cast=int)
redis_password = config("REDIS_PASSWORD", default="")
redis_db = config("REDIS_DB", default=0, cast=int)

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
    db=redis_db,
    encoding='utf-8'
)

task_queue = Queue(
    connection=redis_client,
    default_timeout=300
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_ai_request(user_id: int, message_text: str, system_prompt: str = None) -> Dict[str, Any]:
    try:
        logger.info(f"Processing AI request - User: {user_id}, Message: {message_text[:50]}...")
        
        from ai_service import OllamaService
        
        ai_service = OllamaService()
        
        if not ai_service.ensure_model_ready():
            return {
                'success': False,
                'error': 'AI model not ready',
                'user_id': user_id
            }
        
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant. Provide short and clear answers in Turkish."
        
        result = ai_service.generate_response(message_text, system_prompt)
        result['user_id'] = user_id
        
        logger.info(f"AI response generated - User: {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"AI processing error - User: {user_id}, Error: {e}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'response': "An error occurred. Please try again later."
        }

def get_job_status(job_id: str) -> Dict[str, Any]:
    try:
        job = Job.fetch(job_id, connection=redis_client)
        
        status_info = {
            'job_id': job_id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        }
        
        if job.is_finished:
            try:
                result = job.result
                if result is None:
                    status_info['result'] = {'error': 'Result not found'}
                else:
                    status_info['result'] = result
            except Exception as e:
                logger.error(f"Job result processing error: {e}")
                status_info['result'] = {'error': 'Result could not be processed'}
                
        elif job.is_failed:
            try:
                error = str(job.exc_info)
                status_info['error'] = error
            except Exception as e:
                logger.error(f"Job error processing error: {e}")
                status_info['error'] = 'Error detail could not be retrieved'
            
        return status_info
        
    except Exception as e:
        logger.error(f"Job status check error: {e}")
        return {
            'job_id': job_id,
            'status': 'unknown',
            'error': str(e)
        }

def enqueue_ai_request(user_id: int, message_text: str, system_prompt: str = None) -> str:
    try:
        safe_message = str(message_text)
        safe_prompt = str(system_prompt) if system_prompt else None
        
        import hashlib
        content_hash = hashlib.md5(f"{user_id}_{safe_message}".encode()).hexdigest()[:8]
        job_id = f"ai_request_{user_id}_{content_hash}"
        
        job = task_queue.enqueue(
            process_ai_request,
            user_id,
            safe_message,
            safe_prompt,
            job_timeout=300,
            job_id=job_id
        )
        
        logger.info(f"AI request enqueued - Job ID: {job.id}, User: {user_id}")
        return job.id
        
    except Exception as e:
        logger.error(f"Enqueue error: {e}")
        raise

def get_queue_stats() -> Dict[str, Any]:
    try:
        return {
            'queue_length': len(task_queue),
            'failed_jobs': len(task_queue.failed_job_registry),
            'finished_jobs': len(task_queue.finished_job_registry),
            'started_jobs': len(task_queue.started_job_registry),
            'deferred_jobs': len(task_queue.deferred_job_registry),
        }
    except Exception as e:
        logger.error(f"Queue stats error: {e}")
        return {'error': str(e)}

def clear_finished_jobs():
    try:
        task_queue.finished_job_registry.clear()
        task_queue.failed_job_registry.clear()
        logger.info("Finished jobs cleared")
    except Exception as e:
        logger.error(f"Job clearing error: {e}")