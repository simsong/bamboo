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

import bamboo.face as face
from bamboo.frame import Frame,Tag

def test_scale_from_center():
    assert face.scale_from_center( xy=(23,1695), w=163, h=256, scale=1.3, make_ints=True) == ( (0,1717), 210, 332 )
