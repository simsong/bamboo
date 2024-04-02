"""
Tests for the application
"""


import pytest
import sys
import os
import bottle
import logging
import json
import subprocess
import uuid
import tempfile

from os.path import abspath, dirname

import xml.etree.ElementTree

# https://bottlepy.org/docs/dev/recipes.html#unit-testing-bottle-applications

from boddle import boddle

sys.path.append(dirname(dirname(abspath(__file__))))

from paths import STATIC_DIR,TEST_DATA_DIR
import ingest
#import db
#import bottle_api
#import bottle_app
#import auth

#from user_test import new_course,new_user,API_KEY
#from movie_test import new_movie

"""
def test_version():
    # With templates, res is just a string
    with boddle(params={}):
        res = bottle_app.func_ver()
        assert bottle_app.__version__ in res

def test_is_true():
    assert bottle_api.is_true("Y") is True
    assert bottle_api.is_true("f") is False

def test_get_float(mocker):
    mocker.patch("bottle_api.get", return_value="3")
    assert bottle_api.get_float("key")==3
    mocker.patch("bottle_api.get", return_value="xxx")
    assert bottle_api.get_float("key",default=4)==4

def test_get_bool(mocker):
    mocker.patch("bottle_api.get", return_value="YES")
    assert bottle_api.get_bool("key")==True
    mocker.patch("bottle_api.get", return_value="xxx")
    assert bottle_api.get_bool("key",default=False)==False
    mocker.patch("bottle_api.get", return_value=3.4)
    assert bottle_api.get_bool("key",default=True)==True

def test_static_path():
    # Without templates, res is an HTTP response object with .body and .header and stuff
    with boddle(params={}):
        res = bottle_app.static_path('test.txt')
        assert open(os.path.join(STATIC_DIR, 'test.txt'),'rb').read() == res.body.read()

    # Test file not found
    with pytest.raises(bottle.HTTPResponse) as e:
        with boddle(params={}):
            res = bottle_app.static_path('test_not_vound.txt')

def test_icon():
    with boddle(params={}):
        res = bottle_app.favicon()
    assert open(os.path.join(STATIC_DIR, 'favicon.ico'), 'rb').read() == res.body.read()
"""

def test_filename_template():
    with tempfile.NamedTemporaryFile() as tf:
        REFERENCE_TIME = 1711983244.622765
        os.utime(tf.name, (int(REFERENCE_TIME), int(REFERENCE_TIME)))
        name = ingest.filename_template(root="root/", camera="cam1", path=tf.name)
        assert name == "root/cam1/2024-04/20240401-105404"
