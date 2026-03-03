import os
import asyncio
from flask import Flask
from bot import main as run_bot
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_bot_in_thread():
    """Запуск бота в отдельном потоке с собственным event loop"""
    # Создаем новый event loop для потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Запускаем бота
    print("Запускаем бота в отдельном потоке...")
    run_bot()
    
    # Закрываем loop после завершения
    loop.close()

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    print("Бот запущен в фоновом потоке")
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
