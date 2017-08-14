#!/usr/bin/env python

import gtk,gobject,pango

import audio

def gobject_idle_add(f):
  """ Use this as a decorator to delegate call to gtk main loop,
    mainly used for to operate with thread-unsafe gtk methods """
  def _idle_wrapper(*args):
    gobject.idle_add(f,*args, priority=gobject.PRIORITY_HIGH_IDLE+20)
  return _idle_wrapper

class GUIPlayer:
  
  TEST_WAVS=["tests/codeccall.wav","tests/laugh.wav","tests/sultans.wav","tests/subterraneans.wav"]
  TEST_IT=0

  def __init__(self, app):
    self.app = app

    self.mixer_player = self.app.mixer.new_player()
    self.mixer_player.register_stop_callback(self.player_stop_event)
    self.mixer_player.register_status_callback(self.player_status_event)

    # base widget
    frame = gtk.Frame()
    frame.set_size_request(200,200)

    align = gtk.Alignment()
    align.set_padding(5,5,5,5)
    align.add(frame)
    self.frame = frame

    self.widget = align

    # ui
    hbox = gtk.HBox()
    frame.add(hbox)


    vbox = gtk.VBox()
    hbox.pack_start(vbox)

    # PLAY
    button = gtk.ToggleButton("PLAY")
    def _on_button_clicked(w):
      if w.get_active():
        self.mixer_player.play()
      else:
        self.mixer_player.reset()
    button.connect('clicked', _on_button_clicked)
    vbox.pack_start(button)
    self.play_button = button

    # 
    pb = gtk.ProgressBar()
    pb.set_fraction(0)
    pb.set_size_request(-1,15)
    vbox.pack_start(pb,False,False)
    self.progressbar = pb

    # volume gain
    vscale = gtk.HScale()
    vscale.set_range(0,125)
    vscale.set_value(100)
    vscale.set_draw_value(False)
    def _on_scale_changed(widget, scroll, value):
      self.set_player_gain(value/100.0)

    vscale.connect('change-value', _on_scale_changed)
    vbox.pack_start(vscale,False,False)

    # button bar
    hbox = gtk.HBox()
    vbox.pack_start(hbox,False,False)

    # LOOP
    button = gtk.ToggleButton("L")
    def _on_button_clicked(w):
      self.loop_player(w.get_active())
    button.connect('clicked', _on_button_clicked)
    button.set_size_request(40,40)
    hbox.pack_start(button,False,False)

    # MUTE
    button = gtk.ToggleButton("M")
    def _on_button_clicked(w):
      self.mute_player(w.get_active())

    button.connect('clicked', _on_button_clicked)
    button.set_size_request(40,40)
    hbox.pack_start(button,False,False)
    
    # OPEN
    button = gtk.Button("O")
    def _on_button_clicked(w):
      dialog = gtk.FileChooserDialog("Open sample",
                                      self.app.window,
                                      gtk.FILE_CHOOSER_ACTION_OPEN,
                                      (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                      gtk.STOCK_OPEN, gtk.RESPONSE_OK))
      dialog.set_default_response(gtk.RESPONSE_OK)

      ff = gtk.FileFilter()
      ff.set_name(".wav,.mp3")
      ff.add_pattern("*.wav")
      ff.add_pattern("*.mp3")
      dialog.add_filter(ff)

      r = dialog.run()
      if r == gtk.RESPONSE_OK:
        fname = dialog.get_filename()
        self.load_file(fname)

      dialog.destroy()
    button.connect('clicked', _on_button_clicked)
    button.set_size_request(40,40)
    hbox.pack_start(button,False,False)
 
    # CONFIGURE
    button = gtk.Button("C")
    def _on_button_clicked(w):
      dialog = gtk.Dialog("Configure",
                  None,
                  gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                  (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
      
      frame = gtk.Frame("Output interface")
      cb = gtk.combo_box_new_text()
      for device in self.app.mixer.get_devices_using_api():
        cb.append_text(device)
      cb.set_active(0)
      frame.add(cb)
      dialog.vbox.pack_start(frame)
      device_cb = cb
      
      frame = gtk.Frame("Output mode")
      cb = gtk.combo_box_new_text()
      cb.append_text("Stereo")
      cb.append_text("Right")
      cb.append_text("Left")
      cb.set_active(0)
      frame.add(cb)
      dialog.vbox.pack_start(frame)
      mode_cb = cb
      
      dialog.vbox.show_all()

      r = dialog.run()
      if r == gtk.RESPONSE_ACCEPT:
        try:
          self.set_output_device(device_cb.get_active_text())
        except Exception as e:
          print str(e)

      dialog.destroy()

    button.connect('clicked', _on_button_clicked)
    button.set_size_request(40,40)
    hbox.pack_start(button,False,False)
 

    # DEBUG
    fname = GUIPlayer.TEST_WAVS[GUIPlayer.TEST_IT]
    GUIPlayer.TEST_IT+=1
    self.load_file(fname)

  def set_output_device(self, device):
    self.mixer_player.set_output_device(device)

  def load_file(self, filename):
    self.mixer_player.load_wav(filename)
    self.frame.set_label(filename)

  def set_player_gain(self, gain):
    self.mixer_player.set_gain(gain)

  def mute_player(self, b):
    self.mixer_player.mute(b)

  def loop_player(self, b):
    self.mixer_player.set_loop(b)

  @gobject_idle_add
  def player_stop_event(self):
    self.play_button.set_active(False)

  @gobject_idle_add
  def player_status_event(self,level):
    self.progressbar.set_fraction(level)

class SoundBoard:
  
  def __init__(self, mixer):
    self.mixer = mixer

    self.window = gtk.Window()

    self.window.set_geometry_hints(self.window, width_inc=100, height_inc=100)

    self.window.connect('expose-event', self.on_expose_event)
    self.window.connect('check-resize', self.on_check_resize)


    self.table = gtk.Table(2,2,homogeneous=True)
    self.window.add(self.table)

    self.add_player_xy(0,0)
    self.add_player_xy(1,0)
    self.add_player_xy(0,1)
    self.add_player_xy(1,1)

    self.window.show_all()

  def on_check_resize(self, widget):
    pass

  def on_expose_event(self, widget, event):
    pass

  def add_player_xy(self, x, y):
    player = GUIPlayer(self)
    self.table.attach(player.widget,x,x+1,y,y+1)
  
  def run(self):
    gtk.main()


def main():

  gobject.threads_init()

  mixer = audio.SoundBoardMixer()

  sb = SoundBoard(mixer)
  sb.run()


if __name__ == '__main__':
  main()
