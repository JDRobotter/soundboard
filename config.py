#!/usr/bin/env python
import json
import os.path
import sys

class SoundBoardConfig:
  
  def __init__(self):
    self.kvs = {}
    self.pgname = sys.argv[0]
    print "config pgname",self.pgname
    self.filename = os.path.join(os.path.expanduser('~'),'.soundboard.json')
    self.load()

  def key(self, xy, k):
    if xy is None:
      return "%s:global:%s"%(self.pgname,k)
    else:
      x,y = xy
      return "%s:%d:%d:%s"%(self.pgname,x,y,k)

  def set(self, xy, k, v):
    print "set",xy,k,v
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
