
import os
import os.path
import subprocess
import json
from datetime import datetime
import queue
from multiprocessing import Pool
import functools
import uuid
import urllib.parse
import shutil
import mimetypes
from os.path import basename,dirname,join

import boto3
import yaml
import cv2
from lib.ctools.timer import Timer
from similarity.sim1 import img_sim
from constants import C
from ingest import Frame


class Stage


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process an image. Prototype version",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("roots", nargs="*", help='Directories to process. By default, process the config file')
    args = parser.parse_args()
    if args.roots:
        for root in args.roots:
            for frame in Frame.FrameStream(root):
                print(frame)
