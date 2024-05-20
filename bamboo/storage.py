"""
Storage layer for bamboo.
Handles all get and put operations in a single place, so we can easily handle new storage systems.
"""

import urllib.parse
import os
import mimetypes
import boto3
import functools
import logging
from os.path import dirname

@functools.lru_cache(maxsize=4)
def mkdirs(path):
    logging.debug("mkdirs %s",path)
    os.makedirs(path, exist_ok = True)

@functools.lru_cache(maxsize=4)
def s3_client():
    return boto3.session.Session().client( S3 )

def bamboo_save(url, data, mimetype=None):
    o = urllib.parse.urlparse(url)
    logging.debug("url=%s o=%s data=%s",url,o,data)
    if o.scheme=='file' or o.scheme=='':
        mkdirs( dirname(o.path))
        with open(o.path,'wb') as f:
            f.write(data)
    elif o.scheme == 's3':
        if mimetype is None:
            mimetype = mimetypes.gues_type(i.path)
            s3_client().put_object(Body=data,
                                   Bucket=o.netloc,
                                   Key=o.path[1:],
                                   ContentType=mimetype)
    else:
        raise ValueError(f"unknown scheme {o.scheme} in url {url}")


def bamboo_load(url):
    o = urllib.parse.urlparse(new_name)
    if o.scheme=='file' or o.scheme=='':
        with open(o.path,'rb') as f:
            return f.read()
    elif o.scheme == 's3':
        if mimetype is None:
            mimetype = mimetypes.gues_type(i.path)
            s3_client().get_object(Bucket=o.netloc, Key=o.path[1:])['Body'].read()
    elif o.scheme in ['http','https']:
        r = requests.get(urn, timeout=C.DEFAULT_GET_TIMEOUT)
        return r.content
    else:
        raise ValueError(f"unknown scheme {o.scheme} in url {url}")
