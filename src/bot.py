import logging
from collections import defaultdict
from datetime import datetime

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, Updater

import settings
from model import NodeWatch, TooManyNodeWatchesException
from storage import Storage

storage = Storage.default()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def start(update: Update, context: CallbackContext):
    """Start message handler"""
    context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="I'm Aptos node watcher, I'll be watching the status of all your nodes"
    )


def get_watches(update: Update, context: CallbackContext):
    """Get current node watches for user"""
    watches = storage.get_node_watches(update.effective_chat.id)
    if watches:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text='\n'.join(str(w) for w in watches)
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text='No nodes are being watched right now'
        )


def add_watch(update: Update, context: CallbackContext):
    """Add new node watch"""
    try:
        ip = context.args[0]
        storage.upsert_node_watch(NodeWatch(tg_chat_id=update.effective_chat.id, ip=ip))
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"Successfully added node watch: {ip}"
        )
    except TooManyNodeWatchesException:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"Too many nodes are being watched, consider deleting some"
        )


def delete_watch(update: Update, context: CallbackContext):
    """Delete existing node watch"""
    ip = context.args[0]
    storage.delete_node_watch(NodeWatch(tg_chat_id=update.effective_chat.id, ip=ip))
    context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"Successfully deleted node watch: {ip}"
    )


def send_alerts(context: CallbackContext):
    """Periodic job for sending alarms on nodes that have alarms"""
    alarming_watches = storage.get_node_watches_to_send_alarms()
    grouped_alarms = defaultdict(list)
    for w in alarming_watches:
        grouped_alarms[w.tg_chat_id].append(w)
    
    for chat_id, alarms in grouped_alarms.items():
        message = f'❗Node alert❗\n'
        message += '\n'.join(str(a) for a in alarms)
        context.bot.send_message(chat_id=chat_id, text=message)
        for alarm in alarms:
            alarm.alarm_sent = int(datetime.utcnow().timestamp())
            storage.upsert_node_watch(alarm)

def help(update: Update, context: CallbackContext):
    """Help command handler"""
    commands = {
        '/help': 'Get bot\'s commands',
        '/start': 'Start chatting with bot',
        '/add <ip>': 'Add your node\'s IP or host name to watcher (e.g. /add 1.1.1.1)',
        '/del <ip>': 'Delete node watch (e.g. /del 1.1.1.1)',
        '/watches': 'Get nodes\' statuses',
    }
    context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text='\n'.join(f'{command} - {description}' for command, description in commands.items())
    )

def run():
    updater = Updater(token=settings.TG_BOT_TOKEN, use_context=True)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('watches', get_watches))
    updater.dispatcher.add_handler(CommandHandler('add', add_watch))
    updater.dispatcher.add_handler(CommandHandler('del', delete_watch))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.job_queue.run_repeating(send_alerts, interval=600, first=10)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    run()
