import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = 'TELEGRAM_TOKEN'
WARNS_FILE = 'warns.json'

# Загрузка предупреждений из файла
def load_warns():
    try:
        with open(WARNS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_warns(warns):
    with open(WARNS_FILE, 'w') as f:
        json.dump(warns, f)

warns = load_warns()

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я бот-модератор.')

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text('Эта команда только для администраторов.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('Чтобы забанить пользователя, ответь этой командой на его сообщение.')
        return

    user_to_ban = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_to_ban.id)
        await update.message.reply_text(f'Пользователь {user_to_ban.full_name} забанен.')
    except Exception as e:
        await update.message.reply_text(f'Ошибка: {e}')

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text('Эта команда только для администраторов.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('Ответь на сообщение пользователя, чтобы замутить его.')
        return

    user_to_mute = update.message.reply_to_message.from_user
    permissions = {
        'can_send_messages': False,
        'can_send_media_messages': False,
        'can_send_polls': False,
        'can_send_other_messages': False,
        'can_add_web_page_previews': False
    }
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_to_mute.id, permissions=permissions)
        await update.message.reply_text(f'Пользователь {user_to_mute.full_name} замьючен.')
    except Exception as e:
        await update.message.reply_text(f'Ошибка: {e}')

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global warns
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text('Эта команда только для администраторов.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('Ответь на сообщение пользователя, чтобы выдать предупреждение.')
        return

    user_to_warn = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    user_id = user_to_warn.id
    key = f"{chat_id}_{user_id}"

    warns[key] = warns.get(key, 0) + 1
    save_warns(warns)

    count = warns[key]
    await update.message.reply_text(f'Пользователь {user_to_warn.full_name} получил предупреждение ({count}/3).')

    if count >= 3:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await update.message.reply_text(f'Пользователь {user_to_warn.full_name} забанен за 3 предупреждения.')
            del warns[key]
            save_warns(warns)
        except Exception as e:
            await update.message.reply_text(f'Не удалось забанить: {e}')

def main():
    application = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('ban', ban))
    app.add_handler(CommandHandler('mute', mute))
    app.add_handler(CommandHandler('warn', warn))
    app.run_polling()

if __name__ == '__main__':

    main()
