from flask import Flask, Response, render_template, jsonify
import pyaudio
from deepgram import DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents, LiveOptions
import httpx
import threading
import queue

DEEPGRAM_API_KEY = '1aaae29aee1dd42607c6064bcb3b0785d6d9bb15'
URL = 'http://192.168.1.5:5454/audio'

app = Flask(__name__)

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024

audio_stream = pyaudio.PyAudio()
words_queue = queue.Queue()

def genHeader(sampleRate, bitsPerSample, channels):
    datasize = 2000 * 10 ** 6
    o = bytes("RIFF", 'ascii')
    o += (datasize + 36).to_bytes(4, 'little')
    o += bytes("WAVE", 'ascii')
    o += bytes("fmt ", 'ascii')
    o += (16).to_bytes(4, 'little')
    o += (1).to_bytes(2, 'little')
    o += (channels).to_bytes(2, 'little')
    o += (sampleRate).to_bytes(4, 'little')
    o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4, 'little')
    o += (channels * bitsPerSample // 8).to_bytes(2, 'little')
    o += (bitsPerSample).to_bytes(2, 'little')
    o += bytes("data", 'ascii')
    o += (datasize).to_bytes(4, 'little')
    return o

def get_access_api(data):
    print("Received data:", data)
    words_queue.put(data)

def main():
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = deepgram.listen.live.v('1')

        def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) > 0:
                get_access_api(sentence)

        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

        options = LiveOptions(
            smart_format=True, model="nova-2", language="en-GB"
        )
        dg_connection.start(options)

        lock_exit = threading.Lock()
        exit = False

        def myThread():
            with httpx.stream('GET', URL) as r:
                for data in r.iter_bytes():
                    lock_exit.acquire()
                    if exit:
                        break
                    lock_exit.release()
                    dg_connection.send(data)

        myHttp = threading.Thread(target=myThread)
        myHttp.start()

        # Keep the function running by joining the thread
        myHttp.join()

        dg_connection.finish()

    except Exception as e:
        print(f'Could not open socket: {e}')

def Sound():
    bitspersample = 16
    wav_hader = genHeader(RATE, bitspersample, 2)
    stream = audio_stream.open(format=FORMAT, channels=2, rate=RATE, input=True, input_device_index=1,
                               frames_per_buffer=CHUNK)
    first_run = True
    while True:
        if first_run:
            data = wav_hader + stream.read(CHUNK)
            first_run = False
        else:
            data = stream.read(CHUNK)
        yield (data)

@app.route('/')
def index():
    # Start the transcription process in a separate thread
    threading.Thread(target=main).start()
    return render_template("index.html")

@app.route("/audio")
def audio():
    p = Response(Sound())
    return p

@app.route('/get_data')
def get_data():
    if not words_queue.empty():
        data = words_queue.get()
        return jsonify(data)
    else:
        return jsonify({"error": "No data available"})

if __name__ == "__main__":
    app.run(host="192.168.1.5", port=5454, threaded=True)
