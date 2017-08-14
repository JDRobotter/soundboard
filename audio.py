import pyaudio,wave,time
from threading import Thread
import numpy as np

class MixerPlayer:
  def __init__(self, p):
    self.p = p
    self.stream = None
    self.filename = None

    self.muted = False
    self.loop = False
    self.gain = 1.0

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

    # load wave file
    wf = wave.open(self.filename, 'rb')
    sw = wf.getsampwidth()
    n = wf.getnchannels()
    rate = wf.getframerate()
    print "reset",self.filename,sw,n,rate
    # prepare stream
    def callback(in_data, frame_count, time_info, status):
      data = wf.readframes(frame_count)
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
      if len(data) != sw*n*frame_count:
        # last frame
        
        if self.loop:
          # reload sample, load missing frames from beginning
          wf.rewind()
          data = wf.readframes(frame_count - len(data)/(sw*n))
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
      print len(data)
      return (data, rv)

    # create stream, do not start it
    self.stream = self.p.open(format=self.p.get_format_from_width(sw),
                                channels=n,
                                rate=rate,
                                output=True,
                                stream_callback=callback,
                                start=False)
  
  def play(self):
    self.stream.start_stream()

  def stop(self):
    self.stream.stop_stream()

  def mute(self, b):
    self.muted = b

  def set_loop(self, b):
    self.loop = b

  def set_gain(self, gain):
    self.gain = gain

class SoundBoardMixer:

  def __init__(self):
    self.p = pyaudio.PyAudio()
  
  def new_player(self):
    return MixerPlayer(self.p)
