"""
Stage implementation and some simple stages.
"""

import sys
import os
import time
import math
import collections
import uuid
import shelve
import pickle
import logging
from collections import defaultdict
from abc import ABC,abstractmethod
from filelock import FileLock

from .frame import Frame,FrameTagDict

DEFAULT_JPG_TEMPLATE="frame{counter:08}.jpg"
DEFAULT_JSON_TEMPLATE="frame{counter:08}.json"

def validate_stage(stage):
    if not hasattr(stage,'count'):
        raise RuntimeError(str(stage) + "did not call super().__init__()")

class Stage(ABC):
    """Abstract base class for processing DAG"""

    registered_stages = []

    def __init__(self):
        self.next_stages = set()
        self.config  = {}
        self.sum_t   = 0
        self.sum_t2  = 0
        self.count   = 0
        self.pipeline = None    # my pipeline
        self.registered_stages.append(self)

    @abstractmethod
    def process(self, f:Frame):
        """Called to process. Default behavior is to copy frame to output."""
        self.output(f)


    def _run_frame(self,f):
        """called at the start of processing of this stage.
        Processes and then passes the frame to the output stages."""
        t0 = time.time()
        self.process(f)
        t = time.time() - t0
        self.sum_t  += t
        self.sum_t2 += (t*t)
        self.count  += 1

    def output(self,f):
        """output(f) queues f for output when the current stage is done.
        If f is modified, it needs to be copied.
        """
        for s in self.next_stages:
            self.pipeline.queue_output_stage_frame_pair( (s,f) )

    def pipeline_shutdown(self):
        """Callwed when pipeline is being shut down."""

    @property
    def t_mean(self):
        return self.sum_t / self.count if self.count>0 else float("nan")

    @property
    def t2_mean(self):
        return self.sum_t2 / self.count if self.count>0 else float("nan")

    @property
    def t_variance(self):
        return self.t2_mean - self.t_mean * self.t_mean

    @property
    def t_stddev(self):
        return math.sqrt(self.t_variance)


class ShowFrames(Stage):
    """Pipeline that shows every frame coming through, and then copy to outpu"""
    wait = None
    def __init__(self, wait=None):
        super().__init__()
        if wait is not None:
            self.wait=wait
    def process(self, f:Frame):
        f.show(title=f.src, wait=self.wait)
        self.output(f)


class ShowTags(Stage):
    """Pipeline that shows the tags for every frame that has a tag, and then copy to output"""
    wait = None
    def __init__(self, wait=None):
        super().__init__()
        if wait is not None:
            self.wait=wait
    def process(self, f:Frame):
        if len(f.tags):
            f.show_tags(title="tagged image", wait=self.wait)
        self.output(f)

class Multiplex(Stage):
    """Simply copies from intputs to outputs. ."""
    def process(self, f:Frame):
        self.output(f)


class FilterFrames(Stage):
    def __init__(self, *, framefilter ):
        """Filter tags according to tagfiler"""
        super().__init__()
        self.framefilter = framefilter

    def process(self, f: Frame):
        if self.framefilter(f):
            self.output(f)


class SaveFramesToDirectory(Stage):
    def __init__(self, root, *, template=DEFAULT_JPG_TEMPLATE, nonstop=False):
        """Save the images to the directory, record the path where written, and move on.
        Format is determined by template.
        :param nonstop: - If True, do not stop for failed writer
        """
        super().__init__()
        self.root     = root
        self.counter  = 0
        self.error_counter = 0
        self.template = template
        self.nonstop  = nonstop

    def process(self, f:Frame):
        f = f.copy()
        path = os.path.join(self.root, self.template.format(counter=self.counter))

        # Save and increment counter
        try:
            self.counter += 1
            f.save(path)        # updates f.path
        except FileNotFoundError as e:
            if self.nonstop:
                logging.error("Could not write %s %s",f.path,str(e))
                self.error_counter += 1
            else:
                raise
        # and copy the frame to the output (we are not a sink!)
        self.output(f)

class WriteFrameObjectsToDirectory(Stage):
    def __init__(self, root, *, template=DEFAULT_JSON_TEMPLATE, nonstop=False):
        """Write the images to the directory, record the path where written, and move on.
        :param nonstop: - If True, do not stop for failed writer
        """
        super().__init__()
        self.root     = root
        self.counter  = 0
        self.error_counter = 0
        self.template = template
        self.nonstop  = nonstop

    def process(self, f:Frame):
        path = os.path.join(self.root, self.template.format(counter=self.counter))

        # Save and increment counter
        try:
            self.counter += 1
            with open( path , "w") as fd:
                fd.write(f.json)

        except FileNotFoundError as e:
            if self.nonstop:
                logging.error("Could not write %s %s",f.path,str(e))
                self.error_counter += 1
            else:
                raise
        # and copy the frame to the output (we are not a sink!)
        self.output(f)


WriteFramesToHTMLGallery_tag="bamboo.stage.WriteFramesToHTMLGallery.tag"
class WriteFramesToHTMLGallery(Stage):
    MAX_IMAGES_PER_CLUSTER = 10
    HTML_HEAD = """
<html>
<style>
img.Image {
max-width:128px;
width:128px;
}
div.images {
 display:flex;
}
</style>
<body>
    """
    HTML_FOOT = "</body></html>\n"
    CLUSTER_START_HTML="\n<div class='cluster'>"
    CLUSTER_TITLE_HTML = "<h2>Cluster {cluster_number}:</h2><p><i>{frames_in_cluster} images</i></p>"
    IMAGES_START_HTML = "<div class='images'>"
    IMAGES_END_HTML = "</div>\n"
    IMAGES_MORE_HTML="..."
    CLUSTER_END_HTML = "</div>\n"
    IMAGE_HTML = "<div class='face'><img src='{urn}' class='Image'/><div class='caption'>{caption}</div></div>"
    def __init__(self, *, path:str, image_width=72, image_height=72):
        """Create an HTML file with all of the frames. Each frame must have a tag called GALLERY_KEY."""
        super().__init__()
        self.path = path
        self.image_width = image_width
        self.image_height = image_height
        self.frames_by_key = defaultdict(list)

    def process(self, f):
        self.frames_by_key[f.gallery_key].append(f)

    def pipeline_shutdown(self):
        self.generate_html_gallery()

    def generate_html_gallery(self):
        with open( self.path, "w") as c:
            c.write(self.HTML_HEAD)
            for (cluster_number,frames) in sorted(self.frames_by_key.items()) :
                c.write(self.CLUSTER_START_HTML)
                c.write(self.CLUSTER_TITLE_HTML.format(cluster_number=cluster_number,
                                                  frames_in_cluster=len(frames)))
                c.write(self.IMAGES_START_HTML)
                for (ct,f) in enumerate(frames):
                    if ct==self.MAX_IMAGES_PER_CLUSTER:
                        c.write( self.IMAGES_MORE_HTML)
                        break
                    t = f.findfirst_tag(WriteFramesToHTMLGallery_tag)
                    if t:
                        caption = t.caption
                        print("caption:",caption)
                    else:
                        caption = ''
                    c.write( self.IMAGE_HTML.format(urn=f.urn, caption=caption))
                c.write(self.IMAGES_END_HTML)
                c.write(self.CLUSTER_END_HTML)
            c.write(self.HTML_FOOT)

def Connect(prev_:Stage, next_:Stage):
    """Make the output of stage prev_ go to next_"""
    validate_stage(prev_)
    validate_stage(next_)
    prev_.next_stages.add(next_)
