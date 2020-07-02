import logging
import collections
import contextlib
import wave
import tempfile
import webrtcvad
import torch
from array import array
import time
import threading
import psutil
import pyaudio
import os

from flowd.metrics import BaseCollector


def normalize(snd_data) -> array:
    """Average the volume out"""
    times = 32767.0 / max(abs(i) for i in snd_data)
    r = array('h')
    for i in snd_data:
        r.append(int(i * times))
    return r


class VoiceActivationDetectionCollector(BaseCollector):
    """
    Voice activity detected﻿
    ---
    Seconds per minute﻿
    """
    metric_name = "Voice Activity Detected (seconds)"

    def __init__(self) -> None:
        self.count = 0  # for interval
        self.is_run = True
        self.stream = None
        with tempfile.NamedTemporaryFile() as f:
            self.path = f.name
        self.vad_mode = 3
        self.vad = webrtcvad.Vad(self.vad_mode)
        self.pipeline = torch.hub.load('pyannote/pyannote-audio', 'sad_ami', pipeline=True)
        self.rate = 16000
        self.chunk_duration_ms = 30  # supports 10, 20 and 30 (ms)
        self.chunk_size = int(self.rate * self.chunk_duration_ms / 1000)  # chunk to read
        self.voiced_frames_rate = 0.9
        self.unvoiced_frames_rate = 0.9
        self.max_voiced_frames = 100
        self.leave = False

    def start_listening(self):
        pa = pyaudio.PyAudio()
        self.stream = pa.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=self.rate,
                              input=True,
                              start=False,
                              frames_per_buffer=self.chunk_size)

    def stop_listening(self):
        self.stream.close()

    def audio_generator(self):
        self.stream.start_stream()
        while not self.leave:
            time.sleep(0.005)
            chunk = self.stream.read(self.chunk_size)
            yield chunk

    def write_wave(self, audio) -> None:
        """Writes a .wav file.
        Takes path, PCM audio data, and sample rate.
        """
        with contextlib.closing(wave.open(self.path, 'wb')) as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.rate)
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

    def frame_generator(self, audio):
        """Generates audio frames from PCM audio data.
        Takes the desired frame duration in milliseconds, the PCM data, and
        the sample rate.
        Yields Frames of the requested duration.
        """
        timestamp = 0.0
        duration = float(self.chunk_duration_ms) / 1000.0
        for a in audio:
            yield VoiceActivationDetectionCollector.Frame(a, timestamp, duration)
            timestamp += duration

    def get_segment(self, voiced_frames):
        return VoiceActivationDetectionCollector.Segment(b''.join([f.bytes for f in voiced_frames]),
                                                         self.get_frames_duration(voiced_frames))

    def vad_collector(self, frame_duration_ms,
                      padding_duration_ms, frames):
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
            is_speech = self.vad.is_speech(frame.bytes, self.rate)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                # If we're NOTTRIGGERED and more than 90% of the frames in
                # the ring buffer are voiced frames, then enter the
                # TRIGGERED state.
                if num_voiced > self.voiced_frames_rate * ring_buffer.maxlen:
                    triggered = True
                    # We want to yield all the audio we see from now until
                    # we are NOTTRIGGERED, but we have to start with the
                    # audio that's already in the ring buffer.
                    for f, s in ring_buffer:
                        voiced_frames.append(f)

                    yield self.get_segment(voiced_frames)
                    voiced_frames = []
                    ring_buffer.clear()
            else:
                # We're in the TRIGGERED state, so collect the audio data
                # and add it to the ring buffer.
                voiced_frames.append(frame)
                if len(voiced_frames) > self.max_voiced_frames:
                    yield self.get_segment(voiced_frames)
                    voiced_frames = []
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                # If more than 90% of the frames in the ring buffer are
                # unvoiced, then enter NOTTRIGGERED and yield whatever
                # audio we've collected.
                if num_unvoiced > self.unvoiced_frames_rate * ring_buffer.maxlen:
                    triggered = False

                    yield self.get_segment(voiced_frames)
                    ring_buffer.clear()
                    voiced_frames = []
        # If we have any leftover voiced audio when we run out of input,
        # yield it.
        if voiced_frames:
            yield self.get_segment(voiced_frames)

    def get_frames_duration(self, frames):
        return len(frames) * self.chunk_duration_ms / 1000

    @staticmethod
    def is_busy() -> bool:
        load = psutil.cpu_percent(percpu=True)
        return min(load) > 50

    def _get_speech_duration(self, segment):
        if self.is_busy():
            return segment.duration
        else:
            self.write_wave(segment.frame_bytes)
            return self.pipeline({'audio': self.path}).get_timeline().duration()

    def _collect_internal(self):
        self.start_listening()
        try:
            segments = self.vad_collector(30, 300, self.frame_generator(self.audio_generator()))

            for i, segment in enumerate(segments):
                self.count += self._get_speech_duration(segment)
        finally:
            self.stop_listening()

    def stop_collect(self) -> None:
        self.leave = True
        os.remove(self.path)

    def start_collect(self) -> None:
        self.leave = False
        self._collect_internal()

    def get_current_state(self) -> tuple:
        logging.debug(f'Voice detected, seconds: {self.count}')
        return self.metric_name, self.count

    def cleanup(self) -> None:
        self.count = 0


if __name__ == '__main__':
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    collector = VoiceActivationDetectionCollector()
    x = threading.Thread(target=collector.start_collect, args=())
    logging.debug("Main    : create and start thread")
    x.start()
    logging.debug("Main    : wait for the thread to finish")
    time.sleep(20)
    logging.debug("Main    : stop collect")
    collector.stop_collect()

    metric_name, value = collector.get_current_state()
    logging.info(f'metric_name {metric_name}')
    logging.info(f'value {value}')

    logging.debug("Main    : cleanup")
    collector.cleanup()
    metric_name, value = collector.get_current_state()
    logging.info(f'metric_name {metric_name}')
    logging.info(f'value {value}')
    assert value == 0
