from asyncio import InvalidStateError
import logging
import time
import wave
import os
import io
import numpy as np
from collections import deque
from pyVoIP.VoIP import CallState
from pyVoIP.speech_processing import text_to_speech
from pyVoIP.openai_utils import transcribe_with_whisper, get_openai_gpt_response, extract_lead_info
from pydub import AudioSegment
import threading
# import webrtcvad

# vad = webrtcvad.Vad()
# vad.set_mode(2)  # Try 0–3 (0 = lenient, 3 = strict). Start with 2 as a balanced mode.

# Setup logging format
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

conversation_history = ""
conversation_context = []

is_playing = False
silence_threshold = 1.0
max_silence_threshold = 10.0
last_speech_time = time.time()
buffer_audio = b""

energy_levels = deque(maxlen=20)
DYNAMIC_NOISE_MARGIN = 0.9

def update_playing_status(duration):
    global is_playing
    time.sleep(duration)
    is_playing = False

# def save_audio_to_wav(audio_data, filename):
#     try:
#         logging.info(f"Start saving audio to {filename}")
#         with wave.open(filename, 'wb') as wf:
#             wf.setnchannels(1)
#             wf.setsampwidth(1)
#             wf.setframerate(8000)
#             wf.writeframes(audio_data)

#         padding_duration = 2000  # 2s
#         original = AudioSegment.from_wav(filename)
#         padded = original + AudioSegment.silent(duration=padding_duration)
#         padded.export(filename, format="wav")
#         logging.info(f"Audio saved successfully to {filename}")
#     except Exception as e:
#         logging.error(f"Error saving audio: {e}")


def get_wav_bytes(audio_data, sample_width=2, frame_rate=8000, channels=1):
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(frame_rate)
        wf.writeframes(audio_data)
    wav_io.seek(0)
    return wav_io


def threaded_play_audio(call, audio_data):
    global is_playing
    is_playing = True
    try:
        logging.info("Playback started (threaded)")
        playback_index = 0
        while call.state == CallState.ANSWERED and playback_index < len(audio_data):
            chunk = audio_data[playback_index:playback_index+160]
            call.write_audio(chunk)
            playback_index += 160
            time.sleep(0.02)
        logging.info("Playback finished")
    except Exception as e:
        logging.error(f"Playback error: {e}")
    finally:
        is_playing = False

def is_speech(audio_bytes):
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    energy = np.mean(audio_array ** 2) if len(audio_array) > 0 else 0
    energy_levels.append(energy)
    if len(energy_levels) == energy_levels.maxlen:
        baseline = np.median(energy_levels)
        threshold = baseline * DYNAMIC_NOISE_MARGIN
        return energy > threshold
    return False

# def vad_is_speech(audio_bytes, sample_rate=8000):
#     # WebRTC VAD requires mono, 16-bit PCM, and 10/20/30ms frames
#     # You must make sure `audio_bytes` is 16-bit PCM
#     try:
#         return vad.is_speech(audio_bytes, sample_rate)
#     except Exception as e:
#         logging.warning(f"VAD error: {e}")
#         return False


def log_interaction(session_id, user_text, bot_response):
    log_dir = f"./output/{session_id}"
    os.makedirs(log_dir, exist_ok=True)
    with open(f"{log_dir}/conversation.txt", "a") as f:
        f.write(f"User: {user_text}\n")
        f.write(f"Bot: {bot_response}\n\n")

def answer(call):
    global is_playing, buffer_audio, last_speech_time, conversation_history, conversation_context

    try:
        logging.info("Call answered")
        call.answer()

        session_id = time.strftime("%Y%m%d_%H%M%S")
        chunk_index = 1
        idle_count = 0
        voice_detected = False
        # silence_start_time = None
        conversation_context.clear()
        conversation_history = ""

        greeting = "Hi! This is UniBot from UniConnect. I'm here to tell you about a special loan offer. Would you like to hear more?"
        # play_audio(call, text_to_speech(greeting))
        threading.Thread(target=threaded_play_audio, args=(call, text_to_speech(greeting))).start()
        last_speech_time = time.time()

        while call.state == CallState.ANSWERED:
            try:
                incoming_audio = call.read_audio(length=160, blocking=True)
                buffer_audio += incoming_audio

                if is_speech(incoming_audio):
                #if vad_is_speech(incoming_audio):
    
                    # logging.info("Voice detected")
                    if not voice_detected:
                        logging.info("Speech started")
                        # silence_start_time = None
                    voice_detected = True
                    last_speech_time = time.time()
                # else:
                    # logging.info("Silence detected")

                if time.time() - last_speech_time > silence_threshold and voice_detected and not is_playing:
                    silence_duration = time.time() - last_speech_time
                    logging.info(f"Silence detected for {silence_duration:.2f}s. Beginning processing")

                    # output_dir = "./output"
                    # if not os.path.exists(output_dir):
                    #     os.makedirs(output_dir)
                        
                    #chunk_filename = f"./output/speech_chunk_{session_id}_{chunk_index}.wav"
                    #save_audio_to_wav(buffer_audio, chunk_filename)
                    audio_wav=get_wav_bytes(buffer_audio)

                    logging.info("Transcription started")
                    text = transcribe_with_whisper(audio_wav)
                    logging.info("Transcription completed")

                    if text:
                        logging.info(f"User said: {text}")
                        conversation_history += f"User: {text}\n"
                        conversation_context.append({"role": "user", "content": text})

                        logging.info("Generating bot response")
                        response = get_openai_gpt_response(text, conversation_context)
                        logging.info(f"Bot: {response}")
                        conversation_context.append({"role": "assistant", "content": response})
                        conversation_history += f"Bot: {response}\n"

                        log_interaction(session_id, text, response)

                        # play_audio(call, text_to_speech(response))
                        threading.Thread(target=threaded_play_audio, args=(call, text_to_speech(response))).start()
                        last_speech_time = time.time()
                        buffer_audio = b""
                        voice_detected = False
                        chunk_index += 1

                        if any(word in text.lower() for word in ["loan", "apply", "yes", "need", "interested", "buy", "want", "help"]):
                            lead_json = extract_lead_info(conversation_context)
                            logging.info(f"Lead info: {lead_json}")
                    else:
                        idle_count += 1
                        logging.info(f"Could not understand. Idle count: {idle_count}")
                        if idle_count > 3:
                            # play_audio(call, text_to_speech("Sorry, I didn't get that. Could you say that again?"))
                            threading.Thread(target=threaded_play_audio, args=(call, text_to_speech("Sorry, I didn't get that. Could you say that again?"))).start()
                            last_speech_time = time.time()
                            idle_count = 0

                elif time.time() - last_speech_time > max_silence_threshold and idle_count > 0:
                    logging.info("Extended silence detected. Sending wakeup message")
                    last_speech_time = time.time()
                    idle_count = 0
                    buffer_audio = b""
                    voice_detected = False
                    # play_audio(call, text_to_speech("Still there? If you're interested in a loan or need help, just say so!"))
                    threading.Thread(target=threaded_play_audio, args=(call, text_to_speech("Still there? If you're interested in a loan or need help, just say so!"))).start()
                    last_speech_time = time.time()

            except Exception as e:
                logging.error(f"Call stream error: {e}")

        call.hangup()
        logging.info("Call ended")

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        call.hangup()

