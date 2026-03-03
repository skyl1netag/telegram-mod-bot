import os
import threading
from flask import Flask
from bot import main as run_bot

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

def start_bot():
    print("Запускаем бота...")
    run_bot()

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    thread = threading.Thread(target=start_bot)
    thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)