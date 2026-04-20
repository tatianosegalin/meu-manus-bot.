import logging
import asyncio
import sqlite3
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# O Render permite esconder o token por segurança, mas por enquanto vamos usar direto:
TELEGRAM_TOKEN = '8411389438:AAF7IFpEyGtFr0Mp2MlxjzbxTisSC7KedaA'
# No Render, a API Key do Manus deve ser configurada nas variáveis de ambiente
client = OpenAI()

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    if user_text.lower().startswith("lembre que"):
        partes = user_text[10:].split(" é ", 1)
        if len(partes) == 2:
            chave, valor = partes[0].strip(), partes[1].strip()
            salvar_memoria(user_id, chave, valor)
            await update.message.reply_text(f"✅ Guardado! {chave} é {valor}.")
            return

    memorias = buscar_memoria(user_id)
    contexto = "\n".join([f"{m[0]}: {m[1]}" for m in memorias]) if memorias else "Nenhuma."

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": f"Você é o Manus. Informações salvas do usuário: {contexto}"},
                {"role": "user", "content": user_text}
            ]
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text("Ops, deu erro!")

if __name__ == '__main__':
    init_db()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
