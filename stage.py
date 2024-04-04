"""
Stage implementation and some simple stages.
"""


from abc import ABC,abstractmethod
from frame import Frame


class Stage(ABC):
    """Abstract base class for processing DAG"""
    def __init__(self):
        self.inputs  = set()
        self.outputs = set()
        self.config  = {}

    def add_input(self, obj):
        self.inputs.add(obj)

    def add_output(self,obj):
        self.outputs.add(obj)

    @abstractmethod
    def process(self, frame:Frame):
        """Called to process"""

    def done(self, f):
        """Called when done processing. Default implementation simply calls process on all of the outputs"""
        for obj in self.outputs:
            obj.process(f)

class ShowTags(Stage):
    """Pipeline that shows the tags for every frame that has a tag"""
    def process(self, f:Frame):
        if len(f.tags):
            f.show_tags(title="tagged image", wait=1)
