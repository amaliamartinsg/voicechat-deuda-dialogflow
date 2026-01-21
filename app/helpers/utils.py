import os
from dotenv import load_dotenv
load_dotenv()

# Set ffmpeg binary from .env if available
ffmpeg_path = os.getenv("FFMPEG_BINARY")
if ffmpeg_path:
    os.environ["FFMPEG_BINARY"] = ffmpeg_path


import torch
import scipy
import whisper
from markitdown import MarkItDown
from transformers import VitsModel, AutoTokenizer

WHISPER_MODEL = "turbo"
AUDIO_FILE = "test.wav"


def text_to_speech(text):
    model = VitsModel.from_pretrained("facebook/mms-tts-spa")
    tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-spa")
    inputs = tokenizer(text, return_tensors="pt")

    with torch.no_grad():
        output = model(**inputs).waveform

        # Guardar el audio modificado
        audio_dir = os.path.join(os.path.dirname(__file__), "..", "audios")
        os.makedirs(audio_dir, exist_ok=True)
        audio_path = os.path.join(audio_dir, AUDIO_FILE)
        scipy.io.wavfile.write(audio_path, 18000, output[0].cpu().numpy())


def speech_to_text(audio_path):
    model = whisper.load_model(WHISPER_MODEL)
    print("Transcribiendo audio con Whisper...")
    result = model.transcribe(audio_path, language='es', fp16=False)
    print("Transcripción completa:", result["text"])
    return result["text"]


def use_markitdown(file_path):
    md = MarkItDown(enable_plugins=True)
    result = md.convert(file_path)
    return result.text_content
