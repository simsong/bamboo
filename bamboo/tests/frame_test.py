"""
Tests for the frame
"""

import pytest
import sys
import os
import logging
import json
import subprocess
import uuid
import tempfile

from os.path import abspath, dirname, join, basename

sys.path.append(join(dirname(dirname(dirname(__file__)))))

from bamboo.frame import Frame,Tag

TEST_DATA_DIR = join(dirname(abspath(__file__)),"data")
ROBERTS_DATA  = join(TEST_DATA_DIR, "2022_Roberts_Court_Formal_083122_Web.jpg")

def test_json():
    t = Tag(tag_type='type1',
            text='text2',
            hi='mom')
    print(" t=",t)
    print("t.json:",t.json)

    assert t.dict() == {'tag_type':'type1', 'text':'text2', 'hi':'mom', 'version':1.0}

    t2 = Tag.fromJSON( t.json )
    print("t2=",t)
    assert t==t2

    f = Frame(path=ROBERTS_DATA)
    f.add_tag(t)
    print(" f=",f)
    print(" f.json=",f.json)
    f2 = Frame.fromJSON( f.json )
    print("f2=",f2)
    assert f==f2

    f3 = f.copy()
    assert f==f3

def test_frame():
    f = Frame(path=ROBERTS_DATA)
    print("f=",f)
    (h,w,d) = shape = f.shape
    fc = f.crop( xy=(50,75), w=125, h=60)
    print("fc=",fc)
    print("fc._img=",fc._img)
    assert fc.shape == (60, 125, 3)
    assert len(fc.history) == 2
    assert fc.history[0]==['path',ROBERTS_DATA]
    assert fc.history[1]==['crop',((50,75), (125,60))]

    assert fc.path is None
    with tempfile.NamedTemporaryFile(suffix='.jpg') as tf:
        fc.save(tf.name)
