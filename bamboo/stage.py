"""
Stage implementation and some simple stages.
"""

import os
import time
import math
import collections
import uuid
import shelve
from abc import ABC,abstractmethod
from filelock import FileLock

from .frame import Frame

DEFAULT_JPG_TEMPLATE="frame{counter:08}.jpg"

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
    def process(self, frame:Frame):
        """Called to process"""

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
    """Simply copies from intputs to outputs. Of course, that's the basic functionality, so we do nothing."""
    def process(self, f:Frame):
        self.output(f)

class WriteFramesToDirectory(Stage):
    def __init__(self, *, root, template=DEFAULT_JPG_TEMPLATE):
        super().__init__()
        self.root = root
        self.counter = 0
        self.template = template
        self.dirsmade = set()
    def process(self, f:Frame):
        fname = os.path.join(self.root, self.template.format(counter=self.counter))
        # make sure directory exists
        dirname = os.path.dirname(fname)
        if dirname not in self.dirsmade:
            os.makedirs( dirname , exist_ok=True )
            self.dirsmade.add(dirname)
        # Save and incrementa counter
        f.save(fname)
        self.counter += 1
        # and copy the frame to the output (we are not a sink!)
        self.output(f)



class SaveTagsToShelf(Stage):
    def __init__(self, *, tagfilter=None, path:str):
        """Saves tags that pass tagfilter to the shelf, with locking"""
        super().__init__()
        self.tagfilter = tagfilter
        self.path      = path
        self.lockfile  = path + ".lock"

    def process(self, f:Frame):
        if self.tagfilter is not None:
            print("f.tags+",f.tags)
            tags = [tag for tag in f.tags if self.tagfilter(tag)]
        else:
            tags = f.tags
        print("tags=",tags)
        if tags:
            with FileLock(self.lockfile) as lock:
                with shelve.open(self.path,writeback=True) as db:
                    for tag in tags:
                        db[str(uuid.uuid4())] = (f.path, f.src, tag)
                        print("saved!")

def Connect(prev_:Stage, next_:Stage):
    """Make the output of stage prev_ go to next_"""
    if not hasattr(prev_,'count'):
        raise RuntimeError(str(prev) + "did not call super().__init__()")
    if not hasattr(next_,'count'):
        raise RuntimeError(str(next_) + "did not call super().__init__()")
    prev_.next_stages.add(next_)
