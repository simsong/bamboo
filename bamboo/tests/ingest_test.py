"""
Tests for the application
"""


import pytest
import sys
import os
import logging
import json
import subprocess
import uuid
import tempfile

from os.path import abspath, dirname, join

import xml.etree.ElementTree

# https://bottlepy.org/docs/dev/recipes.html#unit-testing-bottle-applications

sys.path.append(join(dirname(dirname(dirname(__file__)))))

from paths import STATIC_DIR,TEST_DATA_DIR
import ingest

#from user_test import new_course,new_user,API_KEY
#from movie_test import new_movie


def test_filename_template():
    with tempfile.NamedTemporaryFile() as tf:
        REFERENCE_TIME = 1711983244.622765
        os.utime(tf.name, (int(REFERENCE_TIME), int(REFERENCE_TIME)))
        name = ingest.filename_template(camera="cam1", urn=tf.name)
        assert name == "cam1/2024-04/20240401-105404"
