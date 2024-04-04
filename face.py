"""
A number of stages that work with frames that are tagged with faces.
"""

from frame import Frame,FACE
from stage import Stage

class ExtractFaces(Stage):
    """pull faces out of the pipeline and pass them on"""
    def process(self, f:Frame):
        for t in f.tags:
            if t.type==FACE:
                self.output( f.crop( t.pt1, t.pt2 ))
