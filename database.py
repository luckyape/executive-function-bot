import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client

class Database:
    def __init__(self):
        self.url: str = os.environ.get("SUPABASE_URL", "")
        self.key: str = os.environ.get("SUPABASE_KEY", "")
        self.client: Optional[Client] = None

        if self.url and self.key:
            self.client = create_client(self.url, self.key)

    def is_connected(self) -> bool:
        return self.client is not None

    def upsert_user(self, user_id: int, username: str, timezone: str = 'UTC', manifesto: Optional[str] = None):
        if not self.client: return
        data = {
            "id": user_id,
            "username": username,
            "timezone": timezone,
        }
        if manifesto is not None:
            data["manifesto"] = manifesto

        # Supabase upsert
        self.client.table("users").upsert(data).execute()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        if not self.client: return None
        response = self.client.table("users").select("*").eq("id", user_id).execute()
        if response.data:
            return response.data[0]
        return None

    def update_manifesto(self, user_id: int, manifesto: str):
        if not self.client: return
        self.client.table("users").update({"manifesto": manifesto}).eq("id", user_id).execute()

    def log_message(self, user_id: int, role: str, content: str):
        if not self.client: return
        data = {
            "user_id": user_id,
            "role": role,
            "content": content
        }
        self.client.table("message_logs").insert(data).execute()

    def get_recent_messages(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.client: return []
        # Order by created_at desc to get recent, then reverse to chronological
        response = self.client.table("message_logs")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()

        return sorted(response.data, key=lambda x: x['created_at']) if response.data else []

    def add_task(self, user_id: int, description: str, due_date: Optional[datetime] = None):
        if not self.client: return
        data = {
            "user_id": user_id,
            "description": description,
            "status": "pending"
        }
        if due_date:
            data["due_date"] = due_date.isoformat()

        self.client.table("tasks").insert(data).execute()

    def get_pending_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        if not self.client: return []
        response = self.client.table("tasks")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("status", "pending")\
            .execute()
        return response.data if response.data else []

    def mark_task_done(self, task_id: int):
        if not self.client: return
        self.client.table("tasks").update({"status": "done"}).eq("id", task_id).execute()

    def mark_task_done_by_description(self, user_id: int, description_fragment: str):
        """
        Attempts to find a pending task that matches the description fragment and mark it done.
        This is a heuristic method since we might not have the ID.
        """
        if not self.client: return
        # First fetch pending tasks
        pending = self.get_pending_tasks(user_id)
        for task in pending:
            if description_fragment.lower() in task['description'].lower():
                self.mark_task_done(task['id'])
                return task # Return the task that was marked done
        return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        if not self.client: return []
        response = self.client.table("users").select("*").execute()
        return response.data if response.data else []
