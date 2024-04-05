"""
A number of stages that work with frames that are tagged with faces.
"""

from .frame import Frame,FACE,Tag
from .stage import Stage

class ExtractFaces(Stage):
    """pull faces out of the pipeline and pass them on"""
    scale = 1.0
    def __init__(self, scale=1.0):
        """:param scale: allows a region larger than the recognized face to be selected."""
        super().__init__()
        self.scale = scale

    def process(self, f:Frame):
        count = 0
        for t in f.tags:
            if t.type==FACE:
                # Find the existing center, width and height
                cx     = (t.pt2[0]+t.pt1[0])//2
                cy     = (t.pt2[1]+t.pt1[1])//2
                hwidth  = int((t.pt2[0]-t.pt1[0]) * self.scale //2)
                hheight = int((t.pt2[1]-t.pt1[1]) * self.scale //2)

                # Apply the scale
                pt1 = ( max(cx-hwidth,0),       max(cy-hheight,0) )
                pt2 = ( min(cx+hwidth,f.width), min(cy+hheight, f.height) )
                print("f.width=",f.width,"f.height=",f.height,"cx=",cx,"cy=",cy,"hwidth=",hwidth,"hheight=",hheight,"pt1=",pt1,"pt2=",pt2)

                f2 = f.crop( pt1, pt2 )
                count += 1
                f2.add_tag(Tag('extract',extract_count=count))
                self.output( f2 )
