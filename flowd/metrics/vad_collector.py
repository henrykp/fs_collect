import collections
import contextlib
import wave
import tempfile
import webrtcvad
import torch
from array import array
import time
import signal
import threading
import psutil
import pyaudio

RATE = 16000
CHUNK_DURATION_MS = 30       # supports 10, 20 and 30 (ms)
CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)  # chunk to read
VOICED_FRAMES_RATE = 0.9
UNVOICED_FRAMES_RATE = 0.9
VAD_MODE = 3
MAX_VOICED_FRAMES = 100

leave = False


def handle_int(sig, chunk):
    global leave
    leave = True


def start_listening():
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=RATE,
                     input=True,
                     start=False,
                     # input_device_index=2,
                     frames_per_buffer=CHUNK_SIZE)
    return stream


def stop_listening(stream):
    stream.close()


def audio_generator(stream):
    stream.start_stream()
    while not leave:
        time.sleep(0.005)
        chunk = stream.read(CHUNK_SIZE)
        yield chunk


def normalize(snd_data):
    """Average the volume out"""
    times = 32767.0 / max(abs(i) for i in snd_data)
    r = array('h')
    for i in snd_data:
        r.append(int(i * times))
    return r


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.
    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, frame_bytes, timestamp, duration):
        self.bytes = frame_bytes
        self.timestamp = timestamp
        self.duration = duration


class Segment(object):
    """Represents a "frame" of audio data."""
    def __init__(self, frame_bytes, duration):
        self.frame_bytes = frame_bytes
        self.duration = duration


def frame_generator(audio):
    """Generates audio frames from PCM audio data.
    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.
    Yields Frames of the requested duration.
    """
    timestamp = 0.0
    duration = float(CHUNK_DURATION_MS) / 1000.0
    for a in audio:
        yield Frame(a, timestamp, duration)
        timestamp += duration


def get_segment(voiced_frames):
    return Segment(b''.join([f.bytes for f in voiced_frames]), get_frames_duration(voiced_frames))


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    """Filters out non-voiced audio frames.
    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.
    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.
    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.
    Arguments:
    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).
    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > VOICED_FRAMES_RATE * ring_buffer.maxlen:
                triggered = True
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)

                yield get_segment(voiced_frames)
                voiced_frames = []
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            if len(voiced_frames) > MAX_VOICED_FRAMES:
                yield get_segment(voiced_frames)
                voiced_frames = []
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > UNVOICED_FRAMES_RATE * ring_buffer.maxlen:
                triggered = False

                yield get_segment(voiced_frames)
                ring_buffer.clear()
                voiced_frames = []
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield Segment(b''.join([f.bytes for f in voiced_frames]), get_frames_duration(voiced_frames))


def get_frames_duration(frames):
    return len(frames) * CHUNK_DURATION_MS / 1000


def is_busy():
    load = psutil.cpu_percent(percpu=True)
    return min(load) > 100


def _get_speech_duration(path, pipeline, segment):
    if is_busy():
        return segment.duration
    else:
        write_wave(path, segment.frame_bytes, RATE)
        return pipeline({'audio': path}).get_timeline().duration()


def _collect_internal():
    vad = webrtcvad.Vad(VAD_MODE)
    pipeline = torch.hub.load('pyannote/pyannote-audio', 'sad_ami', pipeline=True)

    stream = start_listening()
    try:
        frames = frame_generator(audio_generator(stream))
        segments = vad_collector(RATE, 30, 300, vad, frames)

        with tempfile.NamedTemporaryFile() as f:
            path = f.name

        s = 0
        for i, segment in enumerate(segments):
            s += _get_speech_duration(path, pipeline, segment)
        print("Total speech length: ", s)
    finally:
        stop_listening(stream)


def stop_collect():
    handle_int(None, None)


def start_collect():
    x = threading.Thread(target=_collect_internal, args=())
    x.start()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_int)
    start_collect()
    print("Listening... (Press Ctrl+C to interrupt)")
    time.sleep(60)
    stop_collect()
