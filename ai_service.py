import ollama
import logging
from decouple import config
from typing import Optional, Dict, Any

class OllamaService:
    def __init__(self):
        self.host = config("OLLAMA_HOST", default="localhost")
        self.port = config("OLLAMA_PORT", default=11434, cast=int)
        self.model = config("OLLAMA_MODEL")
        self.base_url = f"http://{self.host}:{self.port}"
        
        self.client = ollama.Client(host=self.base_url)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def check_model_availability(self) -> bool:
        try:
            models = self.client.list()
            available_models = [model['name'] for model in models['models']]
            return self.model in available_models
        except Exception as e:
            self.logger.error(f"Model check error: {e}")
            return False
    
    def pull_model(self) -> bool:
        try:
            self.logger.info(f"Pulling model: {self.model}")
            self.client.pull(self.model)
            self.logger.info(f"Model successfully pulled: {self.model}")
            return True
        except Exception as e:
            self.logger.error(f"Model pull error: {e}")
            return False
    
    def ensure_model_ready(self) -> bool:
        if not self.check_model_availability():
            self.logger.info(f"Model {self.model} not available, pulling...")
            return self.pull_model()
        return True
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            self.logger.info(f"Generating AI response for: {prompt[:50]}...")
            
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            return {
                'success': True,
                'response': response['message']['content'],
                'model': self.model,
                'tokens': response.get('eval_count', 0),
                'duration': response.get('total_duration', 0)
            }
            
        except Exception as e:
            self.logger.error(f"AI response generation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "Sorry, I cannot respond at the moment. Please try again later."
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        try:
            info = self.client.show(self.model)
            
            def estimate_size(parameters_str):
                try:
                    if 'B' in parameters_str:
                        params = float(parameters_str.replace('B', '')) * 1e9
                    elif 'M' in parameters_str:
                        params = float(parameters_str.replace('M', '')) * 1e6
                    else:
                        params = float(parameters_str)
                    
                    size_bytes = params * 1
                    
                    for unit in ['B', 'KB', 'MB', 'GB']:
                        if size_bytes < 1024.0:
                            return f"{size_bytes:.1f} {unit}"
                        size_bytes /= 1024.0
                    return f"{size_bytes:.1f} TB"
                except:
                    return "Unknown"
            
            parameters = info.get('details', {}).get('parameter_size', 'Unknown')
            estimated_size = estimate_size(parameters) if parameters != 'Unknown' else 'Unknown'
            
            return {
                'success': True,
                'model': self.model,
                'size': estimated_size,
                'parameters': parameters,
                'family': info.get('details', {}).get('family', 'Unknown')
            }
        except Exception as e:
            self.logger.error(f"Model information retrieval error: {e}")
            return {
                'success': False,
                'error': str(e)
            }