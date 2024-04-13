import sys
from os.path import dirname,basename,join,abspath

sys.path.append( dirname(dirname(dirname(abspath(__file__)))))

import bamboo.face_deepface as face_deepface
import bamboo.source as source

def test_source_options():
    s = source.SourceOptions(limit=10, mime_type='foo/bar')
    assert s.limit==10
    assert s.mime_type=='foo/bar'
