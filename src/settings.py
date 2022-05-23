import os

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

WATCHER_THREADS = int(os.environ.get("WATCHER_THREADS", "10"))
MAX_WATCHES_PER_USER = int(os.environ.get("MAX_WATCHES_PER_USER", "1"))
