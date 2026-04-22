import logging
import sqlite3
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Configurações
TELEGRAM_TOKEN = '8411389438:AAF7IFpEyGtFr0Mp2MlxjzbxTisSC7KedaA'
RENDER_URL = 'https://meu-manus-bot.onrender.com'
client = OpenAI( )

# Flask para receber o "cutucão" do Telegram (Webhook)
app = Flask(__name__)

# Banco de Dados
def init_db():
    conn = sqlite3.connect('memoria_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS memoria (user_id INTEGER, chave TEXT, valor TEXT, PRIMARY KEY (user_id, chave))')
    conn.commit()
    conn.close()

def salvar_memoria(user_id, chave, valor):
    conn = sqlite3.connect('memoria_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO memoria (user_id, chave, valor) VALUES (?, ?, ?)', (user_id, chave, valor))
    conn.commit()
    conn.close()

def buscar_memoria(user_id):
    conn = sqlite3.connect('memoria_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chave, valor FROM memoria WHERE user_id = ?', (user_id,))
    resultado = cursor.fetchall()
    conn.close()
    return resultado

# Lógica de resposta do Bot
async def process_update(update_data):
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    update = Update.de_json(update_data, application.bot)
    
    user_text = update.message.text
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    await application.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    if user_text.lower().startswith("lembre que"):
        partes = user_text[10:].split(" é ", 1)
        if len(partes) == 2:
            chave, valor = partes[0].strip(), partes[1].strip()
            salvar_memoria(user_id, chave, valor)
            await application.bot.send_message(chat_id=chat_id, text=f"✅ Guardado! {chave} é {valor}.")
            return

    memorias = buscar_memoria(user_id)
    contexto = "\n".join([f"{m[0]}: {m[1]}" for m in memorias]) if memorias else "Nenhuma."

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": f"Você é o Manus. Informações do usuário: {contexto}"},
                {"role": "user", "content": user_text}
            ]
        )
        await application.bot.send_message(chat_id=chat_id, text=response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Erro: {e}")
        await application.bot.send_message(chat_id=chat_id, text="Ops, tive um probleminha. Tente de novo!")

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
    update_data = request.get_json()
    asyncio.run(process_update(update_data))
    return 'OK', 200

@app.route('/')
def index():
    return "Bot Manus está Online!", 200

if __name__ == '__main__':
    init_db()
    # Configura o Webhook no Telegram
    import requests
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}/{TELEGRAM_TOKEN}" )
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
