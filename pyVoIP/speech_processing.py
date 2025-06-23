import logging
import speech_recognition as sr
from gtts import gTTS
import io
import os
import wave
from pydub import AudioSegment

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./voic-bot-demo-080f5ddb64e6.json"

def speech_to_text(wav_file_path):
    """Converts incoming raw audio to text."""
    recognizer = sr.Recognizer()
    # Load the WAV file
    with sr.AudioFile(wav_file_path) as source:
        audio = recognizer.record(source)  # Record the audio from the file

    try:
        # Try to recognize speech in the audio using Google's speech recognition API
        text = recognizer.recognize_google(audio)
        logging.info(f"Recognized Speech: {text}")
        return text
    except sr.UnknownValueError:
        logging.warning("Speech Recognition could not understand the audio.")
        return ""
    except sr.RequestError as e:
        logging.error(f"Speech Recognition API error: {e}")
        return ""

def text_to_speech(text):
    """Converts text response to speech audio."""
    tts = gTTS(text=text, lang="en")
    audio_stream = io.BytesIO()
    tts.write_to_fp(audio_stream)
    audio_stream.seek(0)

    return convert_mp3_to_wav(audio_stream)

def convert_mp3_to_wav(mp3_stream):
    """Converts MP3 audio to WAV format."""
    import pydub
    audio = pydub.AudioSegment.from_file(mp3_stream, format="mp3")
    audio = audio.set_channels(1).set_frame_rate(8000).set_sample_width(1)
    wav_stream = io.BytesIO()
    audio.export(wav_stream, format="wav")
    wav_stream.seek(0)

    return wav_stream.read()


# def trim_silence(raw_audio_bytes, silence_thresh=-40, min_silence_len=200):
#     from pydub import AudioSegment
#     from pydub.silence import detect_nonsilent

#     audio_segment = AudioSegment(
#         data=raw_audio_bytes,
#         sample_width=2, 
#         frame_rate=8000,
#         channels=1
#     )

#     nonsilent_ranges = detect_nonsilent(audio_segment, 
#                                          min_silence_len=min_silence_len, 
#                                          silence_thresh=silence_thresh)

#     if not nonsilent_ranges:
#         return raw_audio_bytes

#     start, end = nonsilent_ranges[0][0], nonsilent_ranges[-1][1]
#     trimmed = audio_segment[start:end]
#     return trimmed.raw_data

    
