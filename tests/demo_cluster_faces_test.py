import sys
import tempfile
import os
import logging

from os.path import dirname,basename,join,abspath
from subprocess import call

sys.path.append( dirname(dirname(abspath(__file__))))

DATA_DIR = join(dirname(dirname(abspath(__file__))),"data")

import demo_cluster_faces

def test_cluster_faces():
    # We don't clea up the cluster so that you can view it!
    with tempfile.TemporaryDirectory(delete=False) as td:
        os.makedirs( facedir := join(td,'facedir'))
        os.makedirs( tagdir  := join(td,'tagdir'))

    demo_cluster_faces.cluster_faces(rootdir = DATA_DIR, facedir=facedir, tagdir=tagdir, show=False)
    print(td)
    call(['find',td,'-ls'])
