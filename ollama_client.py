"""
Ollama client for Claude Agent.
Provides functions to interact with local Ollama models.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, List

# Configure logging
logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        """Initialize the Ollama client.
        
        Args:
            base_url (str): Base URL for the Ollama API.
            model (str): Default model to use.
        """
        self.base_url = base_url
        self.model = model
        self.api_endpoint = f"{base_url}/api/generate"
        self.chat_endpoint = f"{base_url}/api/chat"
        
    def check_connection(self) -> bool:
        """Check if Ollama is running and accessible.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """Get list of available models from Ollama.
        
        Returns:
            List[str]: List of available model names.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model.get("name") for model in models]
            return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    def generate(self, prompt: str, model: Optional[str] = None, 
                 system: Optional[str] = None, temperature: float = 0.7,
                 max_tokens: int = 2048) -> Dict[str, Any]:
        """Generate text with Ollama.
        
        Args:
            prompt (str): The prompt text.
            model (str, optional): Model name to use. Defaults to the initialized model.
            system (str, optional): System message for the model.
            temperature (float): Sampling temperature. Defaults to 0.7.
            max_tokens (int): Maximum tokens to generate. Defaults to 2048.
            
        Returns:
            Dict[str, Any]: Response from Ollama.
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(self.api_endpoint, json=payload)
            if response.status_code == 200:
                return {
                    "success": True,
                    "text": response.json().get("response", ""),
                    "model": model
                }
            else:
                logger.error(f"Error from Ollama API: {response.status_code}, {response.text}")
                return {
                    "success": False,
                    "error": f"Error from Ollama API: {response.status_code}",
                    "model": model
                }
        except Exception as e:
            logger.error(f"Exception when calling Ollama API: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": model
            }

    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
             temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        """Chat with Ollama model.
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries, each with 'role' and 'content' keys.
            model (str, optional): Model name to use. Defaults to the initialized model.
            temperature (float): Sampling temperature. Defaults to 0.7.
            max_tokens (int): Maximum tokens to generate. Defaults to 2048.
            
        Returns:
            Dict[str, Any]: Response from Ollama.
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            response = requests.post(self.chat_endpoint, json=payload)
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": response.json().get("message", {}),
                    "model": model
                }
            else:
                logger.error(f"Error from Ollama API: {response.status_code}, {response.text}")
                return {
                    "success": False,
                    "error": f"Error from Ollama API: {response.status_code}",
                    "model": model
                }
        except Exception as e:
            logger.error(f"Exception when calling Ollama API: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": model
            }

    def process_claude_task(self, prompt: str, todo_content: Optional[str] = None, repo_info: Optional[str] = None,
                           model: Optional[str] = None, temperature: float = 0.7) -> Dict[str, Any]:
        """Process a Claude Agent task using Ollama.
        
        Args:
            prompt (str): The task prompt for Claude.
            todo_content (str, optional): Content of the TODO.md file.
            repo_info (str, optional): Information about the repository.
            model (str, optional): Model name to use. Defaults to the initialized model.
            temperature (float): Sampling temperature. Defaults to 0.7.
            
        Returns:
            Dict[str, Any]: Response including success status and model output.
        """
        model = model or self.model
        
        system_message = """You are Claude, an expert software engineer tasked with completing coding tasks from a TODO list.
Focus on the single task described in the prompt. Work methodically through the problem, create or modify code as needed,
and mark the task for review when complete by changing '[ ]' to '[R]' in the TODO.md file."""
        
        full_prompt = prompt
        
        # Add TODO content if provided
        if todo_content:
            full_prompt += f"\n\nCurrent TODO.md content:\n```md\n{todo_content}\n```"
            
        # Add repo information if provided
        if repo_info:
            full_prompt += f"\n\nRepository information:\n{repo_info}"
            
        return self.generate(
            prompt=full_prompt,
            model=model,
            system=system_message,
            temperature=temperature,
            max_tokens=4096  # Increase token limit for longer responses
        )