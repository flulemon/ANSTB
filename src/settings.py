import os

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

APTOS_TARGET_HOST = os.environ.get("APTOS_TARGET_HOST", "fullnode.devnet.aptoslabs.com")
APTOS_TARGET_PROTO = os.environ.get("APTOS_TARGET_PROTO", "https")
APTOS_TARGET_PORT = int(os.environ.get("APTOS_TARGET_PORT", "443"))

WATCHER_THREADS = int(os.environ.get("WATCHER_THREADS", "10"))
MAX_WATCHES_PER_USER = int(os.environ.get("MAX_WATCHES_PER_USER", "1"))
