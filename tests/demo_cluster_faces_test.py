import sys
from os.path import dirname,basename,join,abspath
from subprocess import call

sys.path.append( dirname(dirname(abspath(__file__))))

DATA_DIR = join(dirname(dirname(abspath(__file__))),"data")

import demo_cluster_faces

def test_cluster_faces():
    # We don't clea up the cluster so that you can view it!
    with tempfile.NamedTemporaryDirectory(delete=False) as td:
        facedir = os.makedirs( join(td,'facedir'))
        tagdir = os.makedirs( join(td,'tagdir'))

    demo_cluster_faces.cluster_faces(rootdir = DATA_DIR, facedir=facedir, tagdir=tagdir, dump=True, show=False)
    print(td)
    call(['find',td,'-ls'])
