"""
A number of stages that work with frames that are tagged with faces.
"""

import logging

from .frame import Frame,TAG_FACE,TAG_FACE_COUNT,Tag
from .stage import Stage

def scale_from_center(*, xy, w, h, scale=1.0, make_ints=True):
    """Given an xy[] point, a width and height, scale it and return a new xy, w, h triple"""
    assert w>=0
    assert h>=0
    center_x = xy[0] + w/2
    center_y = xy[1] + h/2
    new_w = w * scale
    new_h = h * scale
    nxy = (center_x - new_w / 2, center_y - new_w / 2)
    if make_ints:
        new_w = int(new_w)
        new_h = int(new_h)
        nxy = (int(nxy[0]), int(nxy[1]))
    return (nxy, new_w, new_h)


class ExtractFacesToFrames(Stage):
    """Turn each tagged into a frame and pass the frame down the pipeline.
    Consumes the input frames.
    """
    scale = 1.0
    def __init__(self, scale=1.0):
        """:param scale: allows a region larger than the recognized face to be selected."""
        super().__init__()
        self.scale = scale

    def process(self, f:Frame):
        for t in f.tags:
            if t.tag_type==TAG_FACE:
                # Find the existing center, width and height

                (xy, w, h) = scale_from_center( xy=t.xy, w=t.w, h=t.h, scale=self.scale)

                f2 = f.crop( xy=xy, w=w, h=h)
                assert f2.path is None
                f2.add_tag(t)   # add the tag! it has metadata
                assert f2.path is None
                logging.debug("output %s",f2)
                self.output( f2 )
