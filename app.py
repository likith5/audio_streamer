from flask import Flask, render_template, request
import pyaudio
import wave

app = Flask(__name__)

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

audio = pyaudio.PyAudio()
stream = None

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream_audio', methods=['POST'])
def stream_audio():
    start_stream()
    frames = []
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    stop_stream()
    return "Streaming stopped"

if __name__ == '__main__':
    app.run(debug=True)
