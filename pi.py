# app.py
from flask import Flask, Response, render_template, jsonify
import pyaudio
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
import httpx
import threading
import queue

DEEPGRAM_API_KEY = '2085598c756664d156dad8cc47cad493362a5c2b'
URL = 'http://192.168.0.236:5454/audio'
app = Flask(__name__)

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024

audio_stream = pyaudio.PyAudio()
words_queue = queue.Queue()


def genHeader(sampleRate, bitsPerSample, channels):
    datasize = 2000 * 10**6
    o = bytes("RIFF", 'ascii')  # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4, 'little')  # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE", 'ascii')  # (4byte) File type
    o += bytes("fmt ", 'ascii')  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4, 'little')  # (4byte) Length of above format data
    o += (1).to_bytes(2, 'little')  # (2byte) Format type (1 - PCM)
    o += (channels).to_bytes(2, 'little')  # (2byte)
    o += (sampleRate).to_bytes(4, 'little')  # (4byte)
    o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4, 'little')  # (4byte)
    o += (channels * bitsPerSample // 8).to_bytes(2, 'little')  # (2byte)
    o += (bitsPerSample).to_bytes(2, 'little')  # (2byte)
    o += bytes("data", 'ascii')  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4, 'little')  # (4byte) Data size in bytes
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

        myHttp.join()

        dg_connection.finish()

    except Exception as e:
        print(f'Could not open socket: {e}')


def Sound():
    bits_per_sample = 16
    wav_header = genHeader(RATE, bits_per_sample, 2)
    stream = audio_stream.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    first_run = True
    while True:
        if first_run:
            data = wav_header + stream.read(CHUNK)
            first_run = False
        else:
            data = stream.read(CHUNK)
        yield data


@app.route('/')
def index():
    threading.Thread(target=main).start()
    return render_template("index.html")


@app.route("/audio")
def audio():
    return Response(Sound(), mimetype="audio/x-wav")


@app.route('/get_data')
def get_data():
    try:
        data = words_queue.get(timeout=1)
        return jsonify({"data": data})
    except queue.Empty:
        return jsonify({"error": "No data available"})


if __name__ == "__main__":
    app.run(host="192.168.0.236", port=5454, threaded=True)
