import os
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google.cloud import dialogflow_v2 as dialogflow

from dotenv import load_dotenv
load_dotenv()

# ============== CONFIGURACIÓN ==============
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DIALOGFLOW_PROJECT_ID = os.getenv("DIALOGFLOW_PROJECT_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # Path al JSON de credenciales

import tempfile
from helpers.utils import speech_to_text, text_to_speech

# ============== CLIENTE DIALOGFLOW ==============
session_client = dialogflow.SessionsClient()


def detect_intent_text(project_id: str, session_id: str, text: str, language_code: str = "es"):
    """
    Envía texto a Dialogflow y obtiene la respuesta.
    """
    session = session_client.session_path(project_id, session_id)
    
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)
    
    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    
    return response.query_result


# ============== HANDLERS DE TELEGRAM ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "¡Hola! Soy tu asistente conversacional. "
        "Puedes escribirme o enviarme notas de voz."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja mensajes de texto del usuario.
    """
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Mostrar indicador de "escribiendo..."
    await update.message.chat.send_action(action="typing")
    
    try:
        
        print(f"[TEXT] Usuario {user_id}: {user_text}")
        
        # Enviar a Dialogflow
        query_result = detect_intent_text(
            project_id=DIALOGFLOW_PROJECT_ID,
            session_id=str(user_id),
            text=user_text
        )
        
        print(f"[DF] Respuesta: {query_result}")
        
        # Obtener respuesta de Dialogflow
        response_text = query_result.fulfillment_text
        
        if not response_text:
            response_text = "Lo siento, no he entendido tu consulta."
        
        # Enviar respuesta al usuario
        await update.message.reply_text(response_text)
        
    except Exception as e:
        print(f"Error en handle_text: {e}")
        await update.message.reply_text(
            "Ha ocurrido un error procesando tu mensaje. Inténtalo de nuevo."
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja mensajes de voz del usuario.
    Convierte voz → texto → Dialogflow → respuesta (texto o audio)
    """
    user_id = update.effective_user.id
    
    # Mostrar indicador de "grabando audio..."
    await update.message.chat.send_action(action="record_audio")
    
    try:
        # 1. Descargar el audio de Telegram
        print(f"📥 Descargando audio del usuario {user_id}...")
        voice = await update.message.voice.get_file()
        audio_bytes = await voice.download_as_bytearray()
        print(f"✅ Audio descargado: {len(audio_bytes)} bytes")

        # 2. Convertir audio a texto (STT)
        await update.message.chat.send_action(action="typing")
        
        # Guardar en archivo temporal con contexto para asegurar que se cierra
        # Crear carpeta si no existe
        audio_dir = os.path.join(os.path.dirname(__file__), "audios")
        os.makedirs(audio_dir, exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg", dir=audio_dir)
        temp_file.write(bytes(audio_bytes))
        temp_file.close()
        temp_audio_path = os.path.join(audio_dir, temp_file.name)
        print("Guardando archivo temporal en:", temp_audio_path)

        try:
            user_text = speech_to_text(temp_audio_path)
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_audio_path)
            except Exception as cleanup_error:
                print(f"⚠️ No se pudo eliminar archivo temporal: {cleanup_error}")
        
        if not user_text:
            await update.message.reply_text("No he podido entender el audio. Intenta de nuevo. 🎤")
            return
        
        print(f"[STT] Usuario {user_id}: {user_text}")
        
        # 3. Enviar texto a Dialogflow
        query_result = detect_intent_text(
            project_id=DIALOGFLOW_PROJECT_ID,
            session_id=str(user_id),
            text=user_text
        )
        
        response_text = query_result.fulfillment_text

        print(f"[DF] Respuesta: {response_text}")
        
        if not response_text:
            response_text = "Lo siento, no he entendido tu consulta."

        # 4. Enviar respuesta en audio (TTS)
        await update.message.chat.send_action(action="upload_audio")
        try:
            text_to_speech(response_text)
            audio_path = os.path.join(audio_dir, "test.wav")
            with open(audio_path, "rb") as audio_file:
                await update.message.reply_voice(
                    voice=audio_file,
                    caption="Respuesta en audio"
                )
        except Exception as tts_error:
            print(f"Error generando o enviando audio: {tts_error}")
            await update.message.reply_text("No se pudo generar la respuesta en audio.")
        finally:
            # Intentar borrar el archivo de audio generado
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as audio_rm_error:
                print(f"⚠️ No se pudo eliminar test.wav: {audio_rm_error}")

    except Exception as e:
        print(f"Error en handle_voice: {e}")
        traceback.print_exc()
        await update.message.reply_text(
            "Ha ocurrido un error procesando tu audio. Inténtalo de nuevo."
        )


# ============== CONFIGURACIÓN DEL BOT ==============

def main():
    """
    Función principal que inicia el bot.
    """
    # Crear la aplicación
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Registrar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Iniciar el bot
    print("🤖 Bot iniciado. Esperando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()