from __future__ import annotations

from abc import ABC, abstractmethod

import re
from pathlib import Path

from pharaohlib.video import Video
from pharaohlib.frozen import Frozen


class Trigger(ABC):
    @abstractmethod
    def __call__(self, video: Video) -> bool:
        return True


class FilenameTrigger(Frozen, Trigger):
    def __new__(cls, pattern):
        ret = super().__new__(cls, pattern)
        ret.file_pattern = re.compile(pattern)
        return ret

    def __call__(self, video):
        return super().__call__(video) and video.file_name and self.file_pattern.fullmatch(video.file_name)


class IdTrigger(Frozen, Trigger):
    def __new__(cls, id_: str):
        ret = super().__new__(cls, id_)
        ret.id = id_
        return ret

    def __call__(self, video):
        return super().__call__(video)\
               and (self.id == video.paf or self.id == video.paf.videoid)


class Behaviour(Frozen):
    def __new__(cls, *, add: bool = None, remove: bool = None):
        self = super().__new__(cls, add=add, remove=remove)
        self.add = add
        self.remove = remove
        return self

    black: Behaviour
    white: Behaviour


Behaviour.black = Behaviour(add=False)
Behaviour.white = Behaviour(remove=False)
