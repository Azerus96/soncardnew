# storage/github_storage.py

from github import Github
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
import base64

class GitHubStorage:
    def __init__(self):
        """Инициализация хранилища GitHub"""
        self.token = os.getenv('AI_PROGRESS_TOKEN')
        if not self.token:
            raise ValueError("AI_PROGRESS_TOKEN not found in environment variables")
            
        self.repo_name = os.getenv('GITHUB_REPO', 'username/pineapple-poker')
        self.github = Github(self.token)
        self.repo = self.github.get_repo(self.repo_name)
        
    def save_progress(self, data: Dict[str, Any], commit_message: Optional[str] = None) -> bool:
        """
        Сохраняет прогресс ИИ на GitHub
        
        Args:
            data: Словарь с данными для сохранения
            commit_message: Опциональное сообщение коммита
            
        Returns:
            bool: Успешность операции
        """
        try:
            # Подготовка данных
            serialized_data = json.dumps(data, indent=2)
            encoded_data = base64.b64encode(serialized_data.encode()).decode()
            
            # Формирование сообщения коммита
            if not commit_message:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                commit_message = f"Update AI progress - {timestamp}"
                
            # Сохранение текущего состояния
            try:
                contents = self.repo.get_contents("ai_progress/current_state.json")
                self.repo.update_file(
                    contents.path,
                    commit_message,
                    serialized_data,
                    contents.sha
                )
            except:
                self.repo.create_file(
                    "ai_progress/current_state.json",
                    commit_message,
                    serialized_data
                )
                
            # Сохранение в истории
            history_path = f"ai_progress/history/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.repo.create_file(
                history_path,
                f"Historical save - {commit_message}",
                serialized_data
            )
            
            return True
            
        except Exception as e:
            print(f"Error saving to GitHub: {str(e)}")
            return False
            
    def load_progress(self) -> Optional[Dict[str, Any]]:
        """
        Загружает последнее сохраненное состояние
        
        Returns:
            Dict или None: Загруженные данные или None в случае ошибки
        """
        try:
            contents = self.repo.get_contents("ai_progress/current_state.json")
            decoded_content = base64.b64decode(contents.content).decode()
            return json.loads(decoded_content)
        except Exception as e:
            print(f"Error loading from GitHub: {str(e)}")
            return None
            
    def get_progress_history(self, limit: int = 10) -> list:
        """
        Получает историю сохранений
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            list: Список исторических записей
        """
        try:
            contents = self.repo.get_contents("ai_progress/history")
            history = []
            
            for content in sorted(contents, key=lambda x: x.path, reverse=True)[:limit]:
                try:
                    decoded_content = base64.b64decode(content.content).decode()
                    data = json.loads(decoded_content)
                    history.append({
                        'timestamp': content.path.split('/')[-1].split('.')[0],
                        'data': data
                    })
                except:
                    continue
                    
            return history
            
        except Exception as e:
            print(f"Error getting history: {str(e)}")
            return []
            
    def clean_old_history(self, keep_last: int = 100):
        """
        Очищает старые исторические записи
        
        Args:
            keep_last: Количество последних записей для сохранения
        """
        try:
            contents = self.repo.get_contents("ai_progress/history")
            sorted_contents = sorted(contents, key=lambda x: x.path)
            
            if len(sorted_contents) > keep_last:
                for content in sorted_contents[:-keep_last]:
                    self.repo.delete_file(
                        content.path,
                        f"Remove old history - {content.path}",
                        content.sha
                    )
                    
        except Exception as e:
            print(f"Error cleaning history: {str(e)}")
            
    def backup_progress(self) -> bool:
        """
        Создает резервную копию текущего состояния
        
        Returns:
            bool: Успешность операции
        """
        try:
            # Загружаем текущее состояние
            current_state = self.load_progress()
            if not current_state:
                return False
                
            # Создаем бэкап
            backup_path = f"ai_progress/backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.repo.create_file(
                backup_path,
                "Create backup",
                json.dumps(current_state, indent=2)
            )
            
            return True
            
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return False
            
    def restore_from_backup(self, backup_timestamp: str) -> bool:
        """
        Восстанавливает состояние из резервной копии
        
        Args:
            backup_timestamp: Временная метка бэкапа
            
        Returns:
            bool: Успешность операции
        """
        try:
            backup_path = f"ai_progress/backups/backup_{backup_timestamp}.json"
            contents = self.repo.get_contents(backup_path)
            
            decoded_content = base64.b64decode(contents.content).decode()
            backup_data = json.loads(decoded_content)
            
            # Восстанавливаем состояние
            return self.save_progress(
                backup_data,
                f"Restore from backup {backup_timestamp}"
            )
            
        except Exception as e:
            print(f"Error restoring from backup: {str(e)}")
            return False
