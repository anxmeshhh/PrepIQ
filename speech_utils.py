"""
Speech utilities for PrepIQ Interview Simulator
Handles speech-to-text and text-to-speech without cloud dependencies
"""

import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import tempfile
import os
import threading
import queue
import time
from pydub import AudioSegment
import io
import base64
import wave

class SpeechToTextManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def transcribe_audio_file(self, audio_file_path):
        """Transcribe audio from file"""
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            
            # Try multiple engines for better accuracy
            transcript = self._recognize_with_fallback(audio)
            return {
                'transcript': transcript,
                'confidence': 0.8,  # Approximate confidence
                'success': True
            }
        except Exception as e:
            return {
                'transcript': '',
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
    
    def transcribe_audio_data(self, audio_data):
        """Transcribe audio from raw data"""
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            result = self.transcribe_audio_file(temp_file_path)
            
            # Clean up
            os.unlink(temp_file_path)
            
            return result
        except Exception as e:
            return {
                'transcript': '',
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
    
    def _recognize_with_fallback(self, audio):
        """Try multiple recognition engines"""
        # Try Google Speech Recognition first (free tier)
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            pass
        
        # Fallback to Sphinx (offline)
        try:
            return self.recognizer.recognize_sphinx(audio)
        except:
            pass
        
        # If all fail, return empty
        return "Could not understand audio"

class TextToSpeechManager:
    def __init__(self, engine='gtts', language='en', rate=150):
        self.engine_type = engine
        self.language = language
        self.rate = rate
        
        if engine == 'pyttsx3':
            self.pyttsx3_engine = pyttsx3.init()
            self._configure_pyttsx3()
        
        self.audio_queue = queue.Queue()
        self.is_speaking = False
    
    def _configure_pyttsx3(self):
        """Configure pyttsx3 engine"""
        voices = self.pyttsx3_engine.getProperty('voices')
        
        # Try to find a female voice
        for voice in voices:
            if any(keyword in voice.name.lower() for keyword in ['female', 'zira', 'hazel', 'karen']):
                self.pyttsx3_engine.setProperty('voice', voice.id)
                break
        
        self.pyttsx3_engine.setProperty('rate', self.rate)
        self.pyttsx3_engine.setProperty('volume', 0.8)
    
    def generate_speech_file(self, text, output_path=None):
        """Generate speech audio file"""
        if not output_path:
            output_path = tempfile.mktemp(suffix='.mp3' if self.engine_type == 'gtts' else '.wav')
        
        try:
            if self.engine_type == 'gtts':
                tts = gTTS(text=text, lang=self.language, slow=False)
                tts.save(output_path)
            else:  # pyttsx3
                self.pyttsx3_engine.save_to_file(text, output_path)
                self.pyttsx3_engine.runAndWait()
            
            return {
                'success': True,
                'file_path': output_path,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'file_path': None,
                'error': str(e)
            }
    
    def speak_text(self, text, callback=None):
        """Speak text directly (for pyttsx3)"""
        if self.engine_type != 'pyttsx3':
            raise ValueError("Direct speech only available with pyttsx3 engine")
        
        def speak_thread():
            self.is_speaking = True
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
            self.is_speaking = False
            if callback:
                callback()
        
        thread = threading.Thread(target=speak_thread)
        thread.daemon = True
        thread.start()
        return thread
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.engine_type == 'pyttsx3' and self.is_speaking:
            self.pyttsx3_engine.stop()
            self.is_speaking = False

class RealTimeSpeechProcessor:
    def __init__(self, callback=None):
        self.callback = callback
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.listen_thread = None
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
    
    def start_listening(self):
        """Start real-time speech recognition"""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_continuously)
        self.listen_thread.daemon = True
        self.listen_thread.start()
    
    def stop_listening(self):
        """Stop real-time speech recognition"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=1)
    
    def _listen_continuously(self):
        """Continuously listen and process speech"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                # Process audio in separate thread to avoid blocking
                threading.Thread(
                    target=self._process_audio,
                    args=(audio,),
                    daemon=True
                ).start()
                
            except sr.WaitTimeoutError:
                # Timeout is expected, continue listening
                continue
            except Exception as e:
                print(f"Listening error: {e}")
                time.sleep(0.1)
    
    def _process_audio(self, audio):
        """Process audio and call callback with result"""
        try:
            # Try to recognize speech
            text = self.recognizer.recognize_google(audio)
            
            if self.callback and text.strip():
                self.callback({
                    'transcript': text,
                    'confidence': 0.8,
                    'is_final': True
                })
                
        except sr.UnknownValueError:
            # Speech was unintelligible
            pass
        except sr.RequestError as e:
            # API error
            print(f"Speech recognition error: {e}")

# Audio format conversion utilities
class AudioConverter:
    @staticmethod
    def webm_to_wav(webm_data):
        """Convert WebM audio data to WAV format"""
        try:
            # Load WebM audio
            audio = AudioSegment.from_file(io.BytesIO(webm_data), format="webm")
            
            # Convert to WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            return wav_buffer.getvalue()
        except Exception as e:
            print(f"Audio conversion error: {e}")
            return None
    
    @staticmethod
    def base64_to_audio_data(base64_string):
        """Convert base64 string to audio data"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            return base64.b64decode(base64_string)
        except Exception as e:
            print(f"Base64 decode error: {e}")
            return None

# Factory function to create speech managers
def create_speech_managers(config=None):
    """Create and configure speech managers"""
    if config is None:
        config = {
            'tts_engine': 'gtts',
            'tts_language': 'en',
            'tts_rate': 150
        }
    
    stt_manager = SpeechToTextManager()
    tts_manager = TextToSpeechManager(
        engine=config.get('tts_engine', 'gtts'),
        language=config.get('tts_language', 'en'),
        rate=config.get('tts_rate', 150)
    )
    
    return stt_manager, tts_manager
