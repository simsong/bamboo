"""
Stage implementation and some simple stages.
"""


import time
import math
import collections
from abc import ABC,abstractmethod

from frame import Frame

class Linear_pipeline:
    def __init__(self, stages:list):
        self.head = stages[0]
        for i in range(len(stages)-1):
            Connect( stages[i], stages[i+1] )
    def start(self, f):
        """Run a frame through the pipeline. This interface will be moved entirely into the pipeline"""
        self.head._start(f)


class Stage(ABC):
    """Abstract base class for processing DAG"""

    registered_stages = []

    def __init__(self):
        self.next_stages = set()
        self.config  = {}
        self.sum_t   = 0
        self.sum_t2  = 0
        self.count   = 0
        self.registered_stages.append(self)
        self.queued_output_stage_frame_pairs = collections.deque()

    @abstractmethod
    def process(self, frame:Frame):
        """Called to process"""

    def _start(self,f):
        """called at the start of processing of this stage.
        Processes and then passes the frame to the output stages."""
        t0 = time.time()
        self.process(f)
        t = time.time() - t0
        self.sum_t  += t
        self.sum_t2 += (t*t)
        self.count  += 1

        # Now pass to the next. This logic needs to be moved into the linear pipeline and have the output function store
        # (s,f) pairs.
        while True:
            try:
                (s,f) = self.queued_output_stage_frame_pairs.pop()
            except IndexError:
                break
            s._start(f)

    def output(self,f):
        """output(f) queues f for output when the current stage is done."""
        for s in self.next_stages:
            self.queued_output_stage_frame_pairs.append( (s,f) )

    @property
    def t_mean(self):
        return self.sum_t / self.count

    @property
    def t2_mean(self):
        return self.sum_t2 / self.count

    @property
    def t_variance():
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

def Connect(prev_:Stage, next_:Stage):
    """Make the output of stage prev_ go to next_"""
    prev_.next_stages.add(next_)
