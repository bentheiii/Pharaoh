from __future__ import annotations

from typing import Iterable, Union

from abc import ABC, abstractmethod

from dataclasses import dataclass
from enum import Enum
import glob
from itertools import count
from io import StringIO, TextIOBase
import json
import os

import pafy

from pharaohlib._utility import normalize_RTL, safe_filename


class Mode(Enum):
    """A mode for phar downloading"""
    # todo delete modes, I don't use them and they're inconsistent.
    video = 'video'
    audio = 'audio'
    both = 'both'


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


@dataclass(frozen=True)
class AddSuggestion(ChangeSuggestion):
    """suggestion to download a video"""
    paf: pafy.pafy.Pafy
    name: str
    phar: Phar
    num: int
    total: int

    def accept(self):
        self.phar.download_callback(self.paf, self.name)

    def reject(self):
        self.phar.blacklist.add(self.name)

    def __str__(self):
        return f'({self.num}/{self.total}) download {normalize_RTL(self.paf.title)}'


@dataclass(frozen=True)
class RemoveSuggestion(ChangeSuggestion):
    """suggestion to delete a video"""
    file: str
    phar: Phar

    def accept(self):
        self.phar.remove_callback(self.file)

    def reject(self):
        self.phar.whitelist.add(self.file)

    def __str__(self):
        return f'remove {normalize_RTL(self.file)}'


class Phar:
    """A pharaoh project"""
    class ProtocolException(Exception):
        """When a protocol has rejected a file"""
        pass

    def __init__(self):
        self.source = None
        self.destination = None
        self.destinations = []
        self.mode = Mode.both
        self.blacklist = set()
        self.whitelist = set()
        self.pafy_list = None

    def write(self, buffer=..., protocol=...):
        """write the project to a file"""
        # todo add protocol 1
        if buffer is ...:
            buffer = StringIO()
            self.write(buffer, protocol=protocol)
            return buffer.getvalue()

        if protocol is ...:
            writer = None
            for i in count():
                t = getattr(self, '_write_' + str(i))
                if not t:
                    break
                writer = t
        else:
            writer = getattr(self, '_write_' + str(protocol))

        writer(buffer)

    @classmethod
    def read(cls, buffer, protocol=...) -> 'Phar':
        """read the project from a file"""
        # todo add protocol 1
        if isinstance(buffer, str):
            buffer = StringIO(buffer)
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
    def _read_0(cls, buffer: TextIOBase):
        header = buffer.readline(10)
        if header != 'phr0\n':
            raise cls.ProtocolException
        inner = json.load(buffer)
        ret = cls()
        ret.source = inner['source']
        ret.mode = Mode(inner['mode'])
        ret.blacklist.update(inner['blacklist'])
        ret.whitelist.update(inner['whitelist'])
        ret.destinations.extend(inner['destinations'])
        return ret

    def _write_0(self, buffer: TextIOBase):
        buffer.write('phr0\n')
        inner = {
            'source': self.source,
            'blacklist': list(self.blacklist),
            'whitelist': list(self.whitelist),
            'destinations': self.destinations,
            'mode': self.mode.value
        }
        json.dump(inner, buffer)

    def fetch(self):
        """load data from the environment. loads a home directory and the playlist's info"""
        self.pafy_list = pafy.get_playlist2(self.source)

        for dest in self.destinations:
            if os.path.isdir(dest):
                self.destination = dest
                break
        else:
            raise NotADirectoryError('no suiting destination found')

    def suggest_edits(self) \
            -> Iterable[Union[ChangeSuggestion, str]]:
        """yields messages and edits suggested"""
        remaining = [os.path.basename(n) for n in glob.iglob(os.path.join(self.destination, '*.*'))]
        existing = set(os.path.splitext(r)[0] for r in remaining)
        extant = set()
        total = len(self.pafy_list)
        for i, paf in enumerate(self.pafy_list):
            name = safe_filename(paf.title)
            extant.add(name)
            if name in existing:
                yield f'({i}/{total}) media {normalize_RTL(paf.title)} skipped (already exists)'
            else:
                if name not in self.blacklist:
                    yield AddSuggestion(paf, name, self, i, total)
                else:
                    yield f'({i}/{total}) media {normalize_RTL(paf.title)} skipped (blacklisted)'

        for r in remaining:
            name = os.path.splitext(r)[0]
            if name in extant:
                continue

            if r not in self.whitelist:
                yield RemoveSuggestion(r, self)
            else:
                yield f'remaining file {r} skipped (whitelisted)'

    def download_callback(self, paf: pafy.pafy.Pafy, filename):
        """download a video"""
        try:
            if self.mode == Mode.both:
                stream = paf.getbest()
            elif self.mode == Mode.audio:
                stream = paf.getbestaudio('m4a')
            elif self.mode == Mode.audio:
                stream = paf.getbestvideo()
            else:
                raise Exception('unrecognized mode')
            stream.download(filepath=os.path.join(self.destination, filename + '.' + stream.extension))
            return True
        except OSError as e:
            print(f'error downloading {filename}: {e!r}')
            return False

    def remove_callback(self, file):
        """delete a video"""
        os.remove(os.path.join(self.destination, file))
