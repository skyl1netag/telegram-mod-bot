import logging
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен берется из переменной окружения (настроено в Render)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_TOKEN не найден в переменных окружения!")

WARNS_FILE = 'warns.json'

# Загрузка предупреждений из файла
def load_warns():
    try:
        with open(WARNS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Ошибка при загрузке warns.json: {e}")
        return {}

def save_warns(warns):
    try:
        with open(WARNS_FILE, 'w') as f:
            json.dump(warns, f)
    except Exception as e:
        logger.error(f"Ошибка при сохранении warns.json: {e}")

warns = load_warns()

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка при проверке администратора: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! Я бот-модератор.\n'
        'Используй команды /ban, /mute, /warn (только для администраторов).'
    )

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ban - бан пользователя"""
    # Проверка прав администратора
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text('❌ Эта команда только для администраторов.')
        return

    # Проверка, что команда использована как ответ на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text(
            '❌ Чтобы забанить пользователя, ответь этой командой на его сообщение.'
        )
        return

    user_to_ban = update.message.reply_to_message.from_user
    
    # Не даём забанить самого себя
    if user_to_ban.id == update.effective_user.id:
        await update.message.reply_text('❌ Нельзя забанить самого себя!')
        return

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_to_ban.id)
        await update.message.reply_text(f'✅ Пользователь {user_to_ban.full_name} забанен.')
        logger.info(f"Пользователь {user_to_ban.full_name} забанен в чате {update.effective_chat.id}")
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(f'❌ Ошибка при бане: {error_msg[:100]}')
        logger.error(f"Ошибка бана: {e}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mute - ограничение прав пользователя"""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text('❌ Эта команда только для администраторов.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Ответь на сообщение пользователя, чтобы замутить его.')
        return

    user_to_mute = update.message.reply_to_message.from_user
    
    if user_to_mute.id == update.effective_user.id:
        await update.message.reply_text('❌ Нельзя замутить самого себя!')
        return

    # Права, которые отключаем
    permissions = {
        'can_send_messages': False,
        'can_send_media_messages': False,
        'can_send_polls': False,
        'can_send_other_messages': False,
        'can_add_web_page_previews': False,
        'can_change_info': False,
        'can_invite_users': False,
        'can_pin_messages': False
    }
    
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, 
            user_to_mute.id, 
            permissions=permissions
        )
        await update.message.reply_text(f'✅ Пользователь {user_to_mute.full_name} замьючен.')
        logger.info(f"Пользователь {user_to_mute.full_name} замьючен в чате {update.effective_chat.id}")
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(f'❌ Ошибка при муте: {error_msg[:100]}')
        logger.error(f"Ошибка мута: {e}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /warn - выдача предупреждения"""
    global warns
    
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text('❌ Эта команда только для администраторов.')
        return

    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Ответь на сообщение пользователя, чтобы выдать предупреждение.')
        return

    user_to_warn = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    user_id = str(user_to_warn.id)
    key = f"{chat_id}_{user_id}"

    # Увеличиваем счетчик предупреждений
    warns[key] = warns.get(key, 0) + 1
    save_warns(warns)

    count = warns[key]
    await update.message.reply_text(
        f'⚠️ Пользователь {user_to_warn.full_name} получил предупреждение ({count}/3).'
    )
    logger.info(f"Предупреждение {count}/3 для {user_to_warn.full_name} в чате {chat_id}")

    # Если достигнут лимит - бан
    if count >= 3:
        try:
            await context.bot.ban_chat_member(int(chat_id), int(user_id))
            await update.message.reply_text(
                f'🔨 Пользователь {user_to_warn.full_name} забанен за 3 предупреждения.'
            )
            # Удаляем предупреждения после бана
            if key in warns:
                del warns[key]
                save_warns(warns)
            logger.info(f"Пользователь {user_to_warn.full_name} забанен по лимиту предупреждений")
        except Exception as e:
            error_msg = str(e)
            await update.message.reply_text(f'❌ Не удалось забанить: {error_msg[:100]}')
            logger.error(f"Ошибка бана после предупреждений: {e}")

def main():
    """Главная функция запуска бота"""
    logger.info("=" * 50)
    logger.info("ЗАПУСК БОТА...")
    logger.info("=" * 50)
    
    # Проверка наличия токена
    if not TOKEN:
        logger.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_TOKEN не найден!")
        logger.critical("Проверь переменные окружения в Render")
        return
    
    logger.info(f"✅ Токен найден: {TOKEN[:10]}...{TOKEN[-5:]}")
    
    try:
        # Создание приложения
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Приложение создано")
        
        # Добавление обработчиков команд
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('ban', ban))
        application.add_handler(CommandHandler('mute', mute))
        application.add_handler(CommandHandler('warn', warn))
        logger.info("✅ Обработчики команд добавлены")
        
        logger.info("=" * 50)
        logger.info("🚀 БОТ УСПЕШНО ЗАПУЩЕН И ГОТОВ К РАБОТЕ!")
        logger.info("=" * 50)
        
        # Запуск бота
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.critical(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}")
        raise

if __name__ == '__main__':
    main()
