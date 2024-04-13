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

from bamboo.frame import Frame

TEST_DATA_DIR = join(dirname(abspath(__file__)),"data")
ROBERTS_DATA  = join(TEST_DATA_DIR, "2022_Roberts_Court_Formal_083122_Web.jpg")

def test_frame():
    f = Frame(path=ROBERTS_DATA)
    fc = f.crop( xy=(50,75), w=125, h=60)
    assert fc.w == 125
    assert fc.h == 60
    assert len(fc.history) == 2
    assert fc.history[0]==('path',ROBERTS_DATA)
    assert fc.history[1]==('crop',((50,75), (125,60)))

    assert fc.path is None
    with tempfile.NamedTemporaryFile(suffix='.jpg') as tf:
        fc.save(tf.name)
