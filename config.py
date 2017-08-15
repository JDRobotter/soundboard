#!/usr/bin/env python
import json
import os.path

class SoundBoardConfig:
  
  def __init__(self):
    self.kvs = {}
    self.filename = os.path.join(os.path.expanduser('~'),'.soundboard.json')
    self.load()

  def key(self, xy, k):
    x,y = xy
    return "%d:%d:%s"%(x,y,k)

  def set(self, xy, k, v):
    self.kvs[self.key(xy,k)] = v
    self.save()

  def get(self, xy, k):
    return self.kvs.get(self.key(xy,k),None)

  def load(self):
    try:
      self.kvs = json.loads(
        open(self.filename,'rb').read()
      )
    except:
      self.kvs = {}

  def save(self):
    open(self.filename,'wb').write(
      json.dumps(self.kvs)
    )