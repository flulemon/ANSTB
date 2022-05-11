from datetime import datetime, timedelta
from typing import List

import supabase

import settings
from model import NodeWatch, TooManyNodeWatchesException


class Storage:
    """Supabase storage"""
    def __init__(self, supabase_url: str, supabase_key: str, max_node_watches_per_user: int = 10) -> None:
        """
        Initialize Supabase storage

        Args:
            supabase_url (str): Supabase DB URL
            supabase_key (str): Supabase key
            max_node_watches_per_user (int): Maximum number of nodes watched per user. Defaults to 10.
        """
        self.supabase = supabase.create_client(supabase_url, supabase_key)
        self.max_node_watches_per_user = max_node_watches_per_user

    def default() -> 'Storage':
        """Default storage initialized using settings from environment variables"""
        return Storage(settings.SUPABASE_URL, settings.SUPABASE_KEY, settings.MAX_WATCHES_PER_USER)

    def get_node_watches_to_run(self, max_age: timedelta) -> List[NodeWatch]:
        """
        Get node watches whose status is out of date

        Args:
            max_age (timedelta): Maximum status age

        Returns:
            List[NodeWatch]: Node watches that need their status to be updated
        """
        max_age = int((datetime.utcnow() - max_age).timestamp())
        watches = (
            self.supabase.table("watches")
            .select("*")
            .lt("checked", max_age)
            .execute()
        )
        return [NodeWatch.from_dict(w) for w in watches.data]

    def get_node_watches_to_send_alarms(self) -> List[NodeWatch]:
        """
        Get node watches that are not ok but whose alarms have not been sent yet

        Returns:
            List[NodeWatch]: Alarming node watches
        """
        watches = (
            self.supabase.table("watches")
            .select("*")
            .is_("is_ok", False)
            .execute()
        )
        watches = (NodeWatch.from_dict(w) for w in watches.data)
        return [w for w in watches if w.alarm_sent < w.modified]

    def get_node_watches(self, tg_chat_id: int) -> List[NodeWatch]:
        """
        Get node watches for user (or telegram chat)

        Args:
            tg_chat_id (int): Telegram chat ID

        Returns:
            List[NodeWatch]: List of user's node watches
        """
        watches = (
            self.supabase.table("watches")
            .select("*")
            .eq("tg_chat_id", tg_chat_id)
            .execute()
        )
        return [NodeWatch.from_dict(w) for w in watches.data]

    def upsert_node_watch(self, node_watch: NodeWatch):
        """
        Add new or update existing node watch

        Args:
            node_watch (NodeWatch): Node watch to upsert
        """
        if self.max_node_watches_per_user > 0:
            current_node_watches = (
                self.supabase.table("watches")
                .select("*", count="exact")
                .eq("tg_chat_id", node_watch.tg_chat_id)
                .execute()
            )
            if current_node_watches.count > self.max_node_watches_per_user:
                raise TooManyNodeWatchesException()
        return (
            self.supabase.table("watches")
            .upsert(node_watch.to_dict())
            .execute()
        )

    def delete_node_watch(self, node_watch: NodeWatch):
        """
        Delete user's existing node watch

        Args:
            node_watch (NodeWatch): Node watch to delete
        """
        return (
            self.supabase.table("watches")
            .delete()
            .eq("tg_chat_id", node_watch.tg_chat_id)
            .eq("ip", node_watch.ip)
            .execute()
        )
