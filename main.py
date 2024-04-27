from flask import Flask, render_template, request, jsonify
import pyaudio
import threading
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

app = Flask(__name__)

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
API_KEY = "YOUR_DEEPGRAM_API_KEY"

audio = pyaudio.PyAudio()
stream = None
transcribed_text = ""

def start_stream():
    global stream
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

def stop_stream():
    global stream
    if stream is not None:
        stream.stop_stream()
        stream.close()

def main():
    try:
        # STEP 1: Create a Deepgram client using the API key
        deepgram = DeepgramClient(API_KEY)

        # STEP 2: Create a websocket connection to Deepgram
        dg_connection = deepgram.listen.live.v("1")

        # STEP 3: Define the event handlers for the connection
        def on_message(self, result, **kwargs):
            global transcribed_text
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) > 0:
                transcribed_text = sentence

        def on_metadata(self, metadata, **kwargs):
            pass

        def on_error(self, error, **kwargs):
            pass

        # STEP 4: Register the event handlers
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        # STEP 5: Configure Deepgram options for live transcription
        options = LiveOptions(
            model="nova-2", 
            language="en-US", 
            smart_format=True,
        )
        
        @app.route('/')
        def index():
            global transcribed_text
            return render_template('index.html', transcribed_text=transcribed_text)

        @app.route('/stream_audio', methods=['POST'])
        def stream_audio():
            start_stream()
            try:
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK)
                    dg_connection.send(data)  # Send audio data to Deepgram
            except Exception as e:
                print(f"Error streaming audio: {e}")
            finally:
                stop_stream()
            return "Streaming stopped"

        if __name__ == '__main__':
            app.run(debug=True)

    except Exception as e:
        print(f"Could not open socket: {e}")
        return

if __name__ == "__main__":
    main()
