import pyaudio,wave,time
import mad
import os
from threading import Thread
import numpy as np

class AudioFile:

  @classmethod
  def load_file(cls, filename):
    basename = os.path.basename(filename)
    _,ext = os.path.splitext(basename)

    if ext == '.mp3':
      return MP3File(filename)

    elif ext == '.wav':
      return WaveFile(filename)

    else:
      return None

  def __init__(self, filename):
    pass

  def get_nchannels(self):
    pass

  def get_samplerate(self):
    pass

  def get_samplewidth(self):
    pass

  def readframes(self):
    pass

  def close(self):
    pass

  def rewind(self):
    pass

class WaveFile(AudioFile):

  def __init__(self, filename):
    self.wf = wave.open(filename, 'rb')

  def get_nchannels(self):
    return self.wf.getnchannels()

  def get_samplerate(self):
    return self.wf.getframerate()

  def get_samplewidth(self):
    return self.wf.getsampwidth()

  def readframes(self, n):
    return self.wf.readframes(n)

  def close(self):
    self.wf.close()

  def rewind(self):
    self.wf.rewind()

class MP3File(AudioFile):

  def __init__(self, filename):
    self.mf = mad.MadFile(filename)
    self.buffer = bytearray()

  def get_nchannels(self):
    return 2

  def get_samplerate(self):
    return self.mf.samplerate()

  def get_samplewidth(self):
    return 2

  def readframes(self,n):
    rsz = 4*n
    while len(self.buffer) < rsz:
      # buffer is missing data to satisfy read size
      block = self.mf.read()
      if block is not None:
        self.buffer += block
      else:
        break

    block = self.buffer[:rsz]
    self.buffer = self.buffer[rsz:]
    return block

  def close(self):
    pass

  def rewind(self):
    self.mf.seek_time(0)
    self.buffer = bytearray()

class MixerPlayer:
  def __init__(self, mixer, p):
    self.p = p
    self.mixer = mixer
    self.stream = None
    self.af = None
    self.filename = None

    self.muted = False
    self.loop = False
    self.gain = 1.0

    self.output_device_index = None

    self.stop_callback = None

  def register_stop_callback(self, f):
    self.stop_callback = f

  def register_status_callback(self, f):
    self.status_callback = f

  def load_wav(self, filename):
    self.filename = filename
    self.reset()

  def reset(self):

    # check if stream is running
    if self.stream is not None and self.stream.is_active():
      self.stream.stop_stream()
      self.stream.close()
      self.af.close()

    # load wave file
    self.af = AudioFile.load_file(self.filename)
    n = self.af.get_nchannels()
    rate = self.af.get_samplerate()
    sw = self.af.get_samplewidth()
    # prepare stream
    def callback(in_data, frame_count, time_info, status):
      data = self.af.readframes(frame_count)
      samples = np.frombuffer(data, dtype=np.int16)

      if self.gain != 1.0:
        samples = self.gain*samples

      # update stream status
      if self.status_callback is not None:
        lvl = np.max(np.abs(samples))
        fv = lvl/(1.0*np.iinfo(np.int16).max)
        self.status_callback(fv)

      # check if last packet was fetched
      rv = pyaudio.paContinue
      if len(data) < sw*n*frame_count:
        # last frame
        
        if self.loop:
          # reload sample, load missing frames from beginning
          self.af.rewind()
          data = self.af.readframes(frame_count - len(data)/(sw*n))
          samples = np.concatenate((samples, np.frombuffer(data, dtype=np.int16)))

        else:
          # stop stream
          rv = pyaudio.paComplete
          if self.stop_callback is not None:
            self.stop_callback()

      # mute sample
      if self.muted:
        samples = 0*samples

      data = np.getbuffer(samples.astype(dtype=np.int16))
      return (data, rv)

    # create stream, do not start it
    print "stream",sw,n,rate,self.output_device_index
    self.stream = self.p.open(format=self.p.get_format_from_width(sw),
                                channels=n,
                                rate=rate,
                                output=True,
                                stream_callback=callback,
                                start=False,
                                output_device_index=self.output_device_index,
                                frames_per_buffer=2048)
  
  def play(self):
    if self.stream is None:
      return
    self.stream.start_stream()

  def stop(self):
    if self.stream is None:
      return
    self.stream.stop_stream()

  def mute(self, b):
    self.muted = b

  def set_loop(self, b):
    self.loop = b

  def set_gain(self, gain):
    self.gain = gain

  def set_output_device(self, device):
    self.output_device_index = self.mixer.get_device_index_by_name(device)
    self.reset()

  def shutdown(self):
    if self.stream is not None:
      self.stream.stop_stream()
      self.stream.close()
    if self.af is not None:
      self.af.close()

class SoundBoardMixer:

  def __init__(self):
    self.p = pyaudio.PyAudio()
  
    self.api_index = self.p.get_default_host_api_info()['index']

  def get_device_index_by_name(self, device):
    for i in xrange(0,self.p.get_device_count()):
      obj = self.p.get_device_info_by_index(i)
      if obj['name'] == device:
        return obj['index']

  def get_devices_using_api(self):
    devices = []
    for i in xrange(0,self.p.get_device_count()):
      obj = self.p.get_device_info_by_index(i)
      if obj['hostApi'] == self.api_index:
        devices.append(obj['name'])
    return devices

  def new_player(self):
    return MixerPlayer(self, self.p)
