"""
Pipeline"
"""

import os
import time
import math
import collections
import sys
from abc import ABC,abstractmethod
import atexit

from .frame import Frame
from .stage import Connect


class Pipeline(ABC):
    """Base pipeline class"""
    def __init__(self):
        self.queued_output_stage_frame_pairs = collections.deque()
        self.head = None
        self.stages = set()

    def queue_output_stage_frame_pair(self, pair):
        self.queued_output_stage_frame_pairs.append(pair)

    def addLinearPipeline(self, stages:list):
        self.head = stages[0]
        self.stages.update(stages)   # collect all stages for printing stats
        for i in range(len(stages)-1):
            stages[i].pipeline = self
            stages[i+1].pipeline = self
            Connect( stages[i], stages[i+1] )
        return (stages[0],stages[-1])

    def process(self, f):
        """Run a frame through the pipeline. This interface will be moved entirely into the pipeline"""
        self.queue_output_stage_frame_pair( (self.head, f))
        self.run_queue()

    def process_list(self, flist):
        for f in flist:
            self.process(f)

    def process_stream(self, fstream):
        for f in fstream:
            self.process(f)

    def print_stats(self, out=sys.stdout):
        for stage in self.stages:
            name = stage.__class__.__name__
            print(f"{name}: calls: {stage.count}  mean: {stage.t_mean}s  stddev: {stage.t_stddev}", file=out)


class SingleThreadedPipeline(Pipeline):
    """Runs the pipeline in the caller's thread. Print stats on exit"""
    def __init__(self, atExitStats=True, out=sys.stdout):
        super().__init__()
        self.atExitStats=atExitStats
        self.out = out

    def run_queue(self):
        # Now pass to the next. This logic needs to be moved into the linear pipeline and have the output function store
        # (s,f) pairs.
        if self.atExitStats:
            atexit.register(self.print_stats, out=self.out)
        while True:
            try:
                (s,f) = self.queued_output_stage_frame_pairs.popleft()
            except IndexError:
                break
            print("run_queue: ",s,f)
            s._run_frame(f)
