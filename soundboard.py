#!/usr/bin/env python

import os.path
import gtk,gobject,pango

from audio import SoundBoardMixer
from config import SoundBoardConfig

def gobject_idle_add(f):
  """ Use this as a decorator to delegate call to gtk main loop,
    mainly used for to operate with thread-unsafe gtk methods """
  def _idle_wrapper(*args):
    gobject.idle_add(f,*args, priority=gobject.PRIORITY_HIGH_IDLE+20)
  return _idle_wrapper

class GUIPlayer:
  
  def __init__(self, app,
                xy = None,
                looped=None, muted=None,
                filename=None, 
                gain=None):
    self.app = app
    self.xy = xy

    self.mixer_player = self.app.mixer.new_player()
    self.mixer_player.register_stop_callback(self.player_stop_event)
    self.mixer_player.register_status_callback(self.player_status_event)

    # base widget
    frame = gtk.Frame()
    w,h = SoundBoard.W, SoundBoard.H
    frame.set_size_request(w-10,h-10)

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
    button = gtk.ToggleButton()
    image = gtk.Image()
    image.set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)
    button.set_image(image)
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
    self.volume_vscale = vscale

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
    self.loop_button = button

    # MUTE
    button = gtk.ToggleButton("M")
    def _on_button_clicked(w):
      self.mute_player(w.get_active())

    button.connect('clicked', _on_button_clicked)
    button.set_size_request(40,40)
    hbox.pack_start(button,False,False)
    self.mute_button = button
    
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
 
    # setup controls
    if looped is not None:
      self.loop_button.set_active(looped)
    if muted is not None:
      self.mute_button.set_active(muted)
    if filename is not None:
      self.load_file(filename)
    if gain is not None:
      self.volume_vscale.set_value(100.0*gain)

  def config_set(self, key, value):
    self.app.config.set(self.xy, key, value)

  def set_output_device(self, device):
    self.mixer_player.set_output_device(device)

  def load_file(self, filename):
    self.mixer_player.load_wav(filename)
    self.frame.set_label(os.path.basename(filename))
    self.config_set('filename',filename)

  def set_player_gain(self, gain):
    gain = min(max(gain,0.0),1.25)
    self.mixer_player.set_gain(gain)
    self.config_set('gain',gain)

  def mute_player(self, b):
    self.mixer_player.mute(b)
    self.config_set('mute',b)

  def loop_player(self, b):
    self.mixer_player.set_loop(b)
    self.config_set('loop',b)

  @gobject_idle_add
  def player_stop_event(self):
    self.play_button.set_active(False)

  @gobject_idle_add
  def player_status_event(self,level):
    self.progressbar.set_fraction(level)

  def destroy(self):
    self.mixer.remove_player(self.mixer_player)

class SoundBoard:
  
  W,H = 200,200

  def __init__(self, mixer, config):
    self.mixer = mixer
    self.config = config

    self.psize = (0,0)
    self.players = {}

    self.window = gtk.Window()

    self.window.connect('expose-event', self.on_expose_event)
    self.window.connect('check-resize', self.on_check_resize)
    self.window.connect('delete-event', self.on_delete_event)

    self.table = gtk.Table(homogeneous=False)

    vbox = gtk.VBox()
    self.window.add(vbox)
 
    # menu
    menu = gtk.Menu()

    mi = gtk.MenuItem("Output device")
    def _item_activated(widget):
      dialog = gtk.Dialog("Choose output device",
                          self.window,
                          gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                          gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))


      cb = gtk.combo_box_new_text()
      devices = self.mixer.get_devices_using_api()
      for device in devices:
        cb.append_text(device)
      cb.set_active(devices.index(self.mixer.get_output_device()))
      dialog.vbox.pack_start(cb)
      
      dialog.vbox.show_all()
      r = dialog.run()

      if r == gtk.RESPONSE_ACCEPT:
        device = cb.get_active_text()
        self.mixer.set_output_device(device)
        config.set(None,'output-device', device)

      dialog.destroy()
    mi.connect("activate", _item_activated)
    menu.append(mi)

    rootmenu = gtk.MenuItem("Configure")
    rootmenu.set_submenu(menu)

    menubar = gtk.MenuBar()
    menubar.append(rootmenu)
    vbox.pack_start(menubar,False,False)

    # table
    vbox.pack_start(self.table)

    wh = self.config.get(None,'window-wh')
    if wh is not None:
      w,h = wh
      self.window.resize(w,h)

    self.menu_height_px = 20

    self.window.set_geometry_hints(self.window,
      min_width=SoundBoard.W, min_height=SoundBoard.H+self.menu_height_px,
      base_width=SoundBoard.W, base_height=SoundBoard.H+self.menu_height_px,
      width_inc=SoundBoard.W, height_inc=SoundBoard.H)

    self.window.show_all()

  def on_check_resize(self, widget):
    rw,rh = self.window.get_size()
    
    w = rw
    h = rh - self.menu_height_px

    n,m = w/SoundBoard.W, h/SoundBoard.H

    if (n,m) == self.psize:
      return

    pn,pm = self.psize
    rm = set()
    for i in xrange(n,pn):
      for j in xrange(0,pm):
        rm.add((i,j))
    for j in xrange(m,pm):
      for i in xrange(0,pn):
        rm.add((i,j))
    
    for i,j in rm:
      self.remove_player_xy(i,j)

    self.psize = (n,m)

    # fetch current size
    self.table.resize(n,m)

    new = set()
    for i in xrange(pn,n):
      for j in xrange(0,m):
        new.add((i,j))
    for j in xrange(pm,m):
      for i in xrange(0,n):
        new.add((i,j))
   
    for i,j in new:
      self.add_player_xy(i,j)

    self.table.show_all()

    # store size in configuration
    self.config.set(None, "window-wh", (rw,rh))

  def on_expose_event(self, widget, event):
    pass

  def on_delete_event(self, widget, event):
    gtk.main_quit()
    return False

  def remove_player_xy(self, x, y):
    player = self.players[(x,y)]
    self.table.remove(player.widget)
    player.destroy()

  def add_player_xy(self, x, y):
    xy = (x,y)
    player = GUIPlayer(self, xy,
                        looped = self.config.get(xy,'loop'),
                        muted = self.config.get(xy,'mute'),
                        filename = self.config.get(xy,'filename'),
                        gain = self.config.get(xy,'gain'))
    self.players[(x,y)] = player
    self.table.attach(player.widget,x,x+1,y,y+1)
  
  def run(self):
    gtk.main()


def main():

  gobject.threads_init()

  config = SoundBoardConfig()
  mixer = SoundBoardMixer()
  mixer.set_output_device(config.get(None,'output-device'))

  sb = SoundBoard(mixer,config)
  sb.run()

if __name__ == '__main__':
  main()
