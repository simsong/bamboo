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
import logging

from .frame import Frame,NotImageError
from .stage import Connect,validate_stage


logger = logging.getLogger(__name__)

class Pipeline(ABC):
    """Base pipeline class"""
    def __init__(self, verbose=False, debug=False):
        self.queued_output_stage_frame_pairs = collections.deque()
        self.head = None
        self.stages = set()
        self.count  = 0
        self.running = False
        self.verbose = verbose
        self.debug   = debug
        if debug:
            logger.setLevel(logging.DEBUG)
        elif verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

    def queue_output_stage_frame_pair(self, pair):
        self.queued_output_stage_frame_pairs.append(pair)

    def addLinearPipeline(self, stages:list):
        [validate_stage(stage) for stage in stages]
        self.head = stages[0]
        self.stages.update(stages)   # collect all stages for printing stats
        for i in range(len(stages)-1):
            stages[i].pipeline = self
            stages[i+1].pipeline = self
            Connect( stages[i], stages[i+1] )

    def process(self, f):
        """Run a frame through the pipeline."""
        if not self.running:
            raise RuntimeError("pipeline not running")
        self.count += 1
        logger.info("== process %s",f)
        self.queue_output_stage_frame_pair( (self.head, f))
        self.run_queue()

    def process_list(self, flist, verbose=None):
        logger.info("== process_list ==")
        old_verbose = self.verbose
        if verbose is not None:
            self.verbose = verbose
        for f in flist:
            self.process(f)
        self.verbose = old_verbose

    def process_stream(self, fstream):
        for f in fstream:
            self.process(f)

    def print_stats(self, out=sys.stdout):
        for stage in self.stages:
            name = stage.__class__.__name__
            print(f"{name}: calls: {stage.count}  mean: {stage.t_mean:.2}s  stddev: {stage.t_stddev:.2}",
                  file=out)

    def __enter__(self):
        self.running = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for stage in self.stages:
            stage.pipeline_shutdown()
        self.print_stats(out=self.out)
        self.running = False
        return False


class SingleThreadedPipeline(Pipeline):
    """Runs the pipeline in the caller's thread. Print stats on exit"""
    def __init__(self, out=sys.stdout, **kwargs):
        super().__init__(**kwargs)
        self.out = out

    def run_queue(self):
        # Now pass to the next. This logic needs to be moved into the linear pipeline
        # and have the output function store (s,f) pairs.
        while True:
            try:
                (s,f) = self.queued_output_stage_frame_pairs.popleft()
            except IndexError:
                break
            logger.debug("<%s> processing %s",s.__class__.__name__,f)
            if self.debug:
                for t in f.tags:
                    logger.debug("   tag %s",t.dict())
            try:
                s._run_frame(f)
            except FileNotFoundError as e:
                print(f"Cannot read '{f.urn}': {e}",file=sys.stderr)
                continue
            except NotImageError as e:
                print(f"Not an image file '{f.urn}': {e}",file=sys.stderr)
                continue
