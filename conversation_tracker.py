"""
Conversation tracker for Claude Agent.
Tracks and manages conversations with Claude or Ollama models.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ConversationTracker:
    """Tracks and manages conversations with AI models."""
    
    def __init__(self, session_id: str, logs_dir: str = "./logs"):
        """Initialize the conversation tracker.
        
        Args:
            session_id (str): The session ID.
            logs_dir (str): Directory to store logs.
        """
        self.session_id = session_id
        self.logs_dir = Path(logs_dir)
        self.session_dir = self.logs_dir / session_id
        self.conversations_dir = self.session_dir / "conversations"
        self.current_conversation_id = None
        
        # Create directories
        self.conversations_dir.mkdir(exist_ok=True, parents=True)
    
    def start_conversation(self, task: Optional[str] = None, task_type: str = "implementation") -> str:
        """Start a new conversation.
        
        Args:
            task (str, optional): The task associated with the conversation.
            task_type (str): Type of task (implementation or review).
            
        Returns:
            str: Conversation ID.
        """
        conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_conversation_id = conversation_id
        
        conversation_data = {
            "conversation_id": conversation_id,
            "session_id": self.session_id,
            "task": task,
            "task_type": task_type,
            "started_at": datetime.now().isoformat(),
            "messages": [],
            "status": "active"
        }
        
        self._save_conversation(conversation_id, conversation_data)
        logger.info(f"Started conversation {conversation_id} for task: {task}")
        
        return conversation_id
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a message to the current conversation.
        
        Args:
            role (str): Role of the sender (user, assistant, system).
            content (str): Message content.
            metadata (Dict[str, Any], optional): Additional metadata.
            
        Returns:
            Dict[str, Any]: The added message.
        """
        if not self.current_conversation_id:
            self.start_conversation()
        
        message = {
            "id": f"msg_{len(self.get_messages()) + 1}",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        conversation_data = self._load_conversation(self.current_conversation_id)
        if conversation_data:
            conversation_data["messages"].append(message)
            self._save_conversation(self.current_conversation_id, conversation_data)
        
        return message
    
    def end_conversation(self, status: str = "completed", summary: Optional[str] = None) -> bool:
        """End the current conversation.
        
        Args:
            status (str): Completion status (completed, failed, etc.).
            summary (str, optional): Summary of the conversation.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.current_conversation_id:
            logger.warning("No active conversation to end")
            return False
        
        conversation_data = self._load_conversation(self.current_conversation_id)
        if not conversation_data:
            return False
        
        conversation_data["status"] = status
        conversation_data["ended_at"] = datetime.now().isoformat()
        
        if summary:
            conversation_data["summary"] = summary
        
        self._save_conversation(self.current_conversation_id, conversation_data)
        logger.info(f"Ended conversation {self.current_conversation_id} with status: {status}")
        
        self.current_conversation_id = None
        return True
    
    def get_messages(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get messages from a conversation.
        
        Args:
            conversation_id (str, optional): Conversation ID. Defaults to current conversation.
            
        Returns:
            List[Dict[str, Any]]: List of messages.
        """
        conversation_id = conversation_id or self.current_conversation_id
        if not conversation_id:
            return []
        
        conversation_data = self._load_conversation(conversation_id)
        if not conversation_data:
            return []
        
        return conversation_data.get("messages", [])
    
    def get_conversation(self, conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a conversation.
        
        Args:
            conversation_id (str, optional): Conversation ID. Defaults to current conversation.
            
        Returns:
            Dict[str, Any]: Conversation data.
        """
        conversation_id = conversation_id or self.current_conversation_id
        if not conversation_id:
            return None
        
        return self._load_conversation(conversation_id)
    
    def list_conversations(self, task: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all conversations for the session.
        
        Args:
            task (str, optional): Filter by task.
            
        Returns:
            List[Dict[str, Any]]: List of conversations.
        """
        conversations = []
        
        for conversation_file in self.conversations_dir.glob("*.json"):
            try:
                with open(conversation_file, 'r') as f:
                    conversation = json.load(f)
                    
                    if task and conversation.get("task") != task:
                        continue
                    
                    conversations.append(conversation)
            except Exception as e:
                logger.error(f"Error loading conversation file {conversation_file}: {e}")
        
        # Sort by started_at (newest first)
        conversations.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        
        return conversations
    
    def _save_conversation(self, conversation_id: str, data: Dict[str, Any]) -> bool:
        """Save conversation data to file.
        
        Args:
            conversation_id (str): Conversation ID.
            data (Dict[str, Any]): Conversation data.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        conversation_file = self.conversations_dir / f"{conversation_id}.json"
        
        try:
            with open(conversation_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving conversation file {conversation_file}: {e}")
            return False
    
    def _load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation data from file.
        
        Args:
            conversation_id (str): Conversation ID.
            
        Returns:
            Dict[str, Any]: Conversation data.
        """
        conversation_file = self.conversations_dir / f"{conversation_id}.json"
        
        if not conversation_file.exists():
            return None
        
        try:
            with open(conversation_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading conversation file {conversation_file}: {e}")
            return None