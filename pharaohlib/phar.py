from __future__ import annotations

import re
from typing import Iterable, Union, Tuple, List, MutableMapping, TextIO, BinaryIO

from abc import ABC, abstractmethod

from dataclasses import dataclass
from itertools import count
from io import BytesIO, StringIO
import json
import os
import warnings
from pathlib import Path
import pickle

import pafy

from pharaohlib._utility import normalize_RTL
from pharaohlib.rules import Behaviour, Trigger, FilenameTrigger, IdTrigger
from pharaohlib.video import Video


class ChangeSuggestion(ABC):
    """A suggestion that the user chan choose to accept or reject"""

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def accept(self):
        pass

    @abstractmethod
    def reject(self):
        pass

    def suggest(self, auto_response):
        if auto_response is None:
            yield self
        else:
            if auto_response:
                self.accept()
                yield str(self)+' [automatically accepted]'
            else:
                self.reject()
                yield str(self) + ' [automatically rejected]'


@dataclass(frozen=True)
class AddSuggestion(ChangeSuggestion):
    """suggestion to download a video"""
    video: Video
    fname: str
    phar: Phar

    def accept(self):
        self.phar.download_callback(self.video.paf, self.fname)

    def reject(self):
        self.phar.rules.append((IdTrigger(self.video.paf.videoid), Behaviour.black))

    def __str__(self):
        return f'download {normalize_RTL(self.video.paf.title)}'


@dataclass(frozen=True)
class RemoveSuggestion(ChangeSuggestion):
    """suggestion to delete a video"""
    file: Path
    phar: Phar

    def accept(self):
        self.phar.remove_callback(self.file)

    def reject(self):
        self.phar.rules.append((FilenameTrigger(re.escape(str(self.file))), Behaviour.white))

    def __str__(self):
        return f'remove {normalize_RTL(str(self.file))}'


class Phar:
    """A pharaoh project"""

    class ProtocolException(Exception):
        """When a protocol has rejected a file_name"""
        pass

    def __init__(self):
        self.source_playlist_id = None
        self.destination_root: Path = None
        self.rules: List[Tuple[Trigger, Behaviour]] = None
        self.id_fname_assoc: MutableMapping[str, str] = None  # file names only

        self.pafy_list: pafy.playlist = None
        self.videos: List[Video] = None

    def get_video(self, id_: str = object(), file: str = object()):
        for v in self.videos:
            if isinstance(v.paf, str):
                vid = v.paf
            else:
                vid = v.paf.videoid
            if (vid == id_) \
                    or (v.file_name == file):
                return v
        return None

    def __getstate__(self):
        return (
            1,
            self.source_playlist_id,
            self.destination_root,
            self.rules,
            self.id_fname_assoc
        )

    def __setstate__(self, state):
        num = state[0]
        if num == 1:
            _, self.source_playlist_id, self.destination_root, self.rules, self.id_fname_assoc = state
            self._fetch()
        else:
            raise self.ProtocolException

    def write(self, buffer=...):
        """write the project to a file_name"""
        if buffer is ...:
            buffer = BytesIO()
            self.write(buffer)
            return buffer.getvalue()

        pickle.dump(self, buffer)

    @classmethod
    def read(cls, buffer, protocol=...) -> 'Phar':
        """read the project from a file_name"""
        if isinstance(buffer, str):
            buffer = StringIO(buffer)
        if isinstance(buffer, bytes):
            buffer = BytesIO(buffer)

        if protocol is ...:
            for prot in count():
                try:
                    read = getattr(cls, '_read_' + str(prot))
                    return read(buffer)
                except cls.ProtocolException:
                    buffer.seek(0)  # reset the reader before trying another one
                    continue
                except AttributeError:
                    raise cls.ProtocolException('no valid protocol found')
        else:
            read = getattr(cls, '_read_' + str(protocol))
            return read(buffer)

    @classmethod
    def _read_0(cls, buffer: TextIO):
        header = buffer.readline(10)
        if header.rstrip() != 'phr0':
            raise cls.ProtocolException
        inner = json.load(buffer)
        ret = cls()

        source: str = inner['source']
        cleanup_prefix = 'https://www.youtube.com/playlist?list='
        if source.startswith(cleanup_prefix):
            source = source[len(cleanup_prefix):]
        ret.source_playlist_id = source

        mode: str = inner['mode']
        if mode != 'both':
            warnings.warn('modes are deprecated, switching to "both" mode')

        ret.rules = []
        if inner['blacklist']:
            warnings.warn('name blacklists are not supported, ignoring blacklist')
        for file_name in inner['whitelist']:
            ret.rules.append((FilenameTrigger(file_name), Behaviour.white))

        if len(inner['destinations']) > 1:
            warnings.warn('multiple destinations are not supported, using first one')
        ret.destination_root = Path(inner['destinations'][0])

        ret.id_fname_assoc = {}
        ret._fetch()
        return ret

    @classmethod
    def _read_1(cls, buffer: BinaryIO):
        try:
            return pickle.load(buffer)
        except pickle.UnpicklingError as e:
            raise cls.ProtocolException from e

    def _fetch(self):
        """load data from the environment. loads a home directory and the playlist's info"""
        self.pafy_list = pafy.get_playlist2(self.source_playlist_id)
        self.videos = []
        assoc = dict(self.id_fname_assoc)
        for paf in self.pafy_list:
            rel_path = assoc.pop(paf.videoid, None)
            video = Video(paf, rel_path)
            self.videos.append(video)
        for id_, rel_path in assoc.items():
            v = self.get_video(id_=id_)
            if v:
                assert v.file_name is None
                v.file_name = rel_path
            else:
                video = Video(id_, rel_path)
                self.videos.append(video)

    def get_behaviour(self, video: Video)->Behaviour:
        for trigger, behaviour in self.rules:
            if trigger(video):
                return behaviour
        return Behaviour()

    def suggest_edits(self) \
            -> Iterable[Union[ChangeSuggestion, str]]:
        """yields messages and edits suggested"""
        # make all remove suggestions
        for v in self.videos:
            if v.exists_in_source:
                # video still exists in playlist
                continue
            match = next(self.destination_root.rglob('**/'+v.file_name), None)
            if not match:
                continue
            b = self.get_behaviour(v)
            s = RemoveSuggestion(match, self)
            yield from (s.suggest(b.remove))

        # make all download suggestions
        for v in self.videos:
            if not v.exists_in_source:
                continue
            dest_fname = v.file_name or (v.suggest_fname()+'.*')
            match = next(self.destination_root.rglob('**/' + dest_fname), None)
            if match:
                if v.file_name is None:
                    v.file_name = match.name
                    self.id_fname_assoc.setdefault(v.paf.videoid, match.name)
                continue
            b = self.get_behaviour(v)
            s = AddSuggestion(v, dest_fname, self)
            yield from (s.suggest(b.add))

    def download_callback(self, paf, filename):
        """download a video"""
        try:
            stream = paf.getbest()
            ext_index = filename.rfind('.')
            if ext_index >= 0 and (len(filename) - ext_index) < 4:
                filename = filename[:ext_index+1] + stream.extension
            else:
                filename += '.' + stream.extension
            fpath = self.destination_root / filename
            stream.download(filepath=fpath)
            self.id_fname_assoc[paf.videoid] = filename
            return True
        except OSError as e:
            print(f'error downloading {filename}: {e!r}')
            return False

    def remove_callback(self, file):
        """delete a video"""
        os.remove(self.destination_root / file)
