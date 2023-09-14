import websockets
import asyncio
import base64
import json
import pyaudio
from configure import auth_key

import streamlit as st

if 'run' not in st.session_state:
    st.session_state['run'] = False

FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()

# starts recording
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER
)


def start_listening():
    st.session_state['run'] = True


def stop_listening():
    st.session_state['run'] = False


st.title('Realtime Transcription')
st.write('*English only')
st.write("Sample Audio [HERE](https://storage.googleapis.com/aai-web-samples/meeting.mp4)")

start, stop = st.columns(2)
start.button('Start Listening', on_click=start_listening)
stop.button('Stop Listening', on_click=stop_listening)

# the AssemblyAI endpoint we're going to hit
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"


def convert_text(textstring):
    separator = ' '
    punctuation = '.,;:?!'
    vowel = 'aeiou'
    words = textstring.split(separator)
    newWords = []

    if len(textstring) != 0:
        print(words)
        for word in words:
            if word[-1] in punctuation:
                if word[-2] in vowel:
                    newWord = word[0:-1] + word[-1]
                    newWords.append(newWord)
                elif word[-2] not in vowel:
                    newWord = word[0:-1] + word[-1]
                    newWords.append(newWord)

            elif word[-1] in vowel:
                newWord = word
                newWords.append(newWord)

            else:
                newWord = word
                newWords.append(newWord)

        newSentence = separator.join(newWords)
        return newSentence


async def send_receive():
    print(f'Connecting websocket to url ${URL}')
    async with websockets.connect(
            URL,
            extra_headers=(("Authorization", auth_key),),
            ping_interval=5,
            ping_timeout=20
    ) as _ws:
        r = await asyncio.sleep(0.1)
        print("Receiving SessionBegins ...")
        session_begins = await _ws.recv()
        print(session_begins)
        print("Sending messages ...")

        async def send():
            while st.session_state['run']:
                try:
                    data = stream.read(FRAMES_PER_BUFFER)
                    data = base64.b64encode(data).decode("utf-8")
                    json_data = json.dumps({"audio_data": str(data)})
                    r = await _ws.send(json_data)
                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"
                r = await asyncio.sleep(0.01)

            return True

        async def receive():
            while st.session_state['run']:
                try:
                    result_str = await _ws.recv()
                    if json.loads(result_str)["message_type"] == 'FinalTranscript':
                        print(convert_text(json.loads(result_str)['text']))
                        st.markdown(convert_text(json.loads(result_str)['text']))
                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"

        send_result, receive_result = await asyncio.gather(send(), receive())


asyncio.run(send_receive())