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
        scipy.io.wavfile.write(AUDIO_FILE, 22050, output[0].cpu().numpy())


def speech_to_text(audio_path):
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(audio_path, language="es")  # Especifica idioma para mejor precisión
    return result["text"].strip()


def use_markitdown(file_path):
    md = MarkItDown(enable_plugins=True)
    result = md.convert(file_path)
    return result.text_content
