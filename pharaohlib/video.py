from typing import Optional, Union

from pathlib import Path
from dataclasses import dataclass

from pafy import pafy

from pharaohlib._utility import safe_filename


@dataclass
class Video:
    paf: Union[pafy.Pafy, str]
    file_name: Optional[str] = None

    @property
    def exists_in_source(self):
        return not isinstance(self.paf, str)

    def suggest_fname(self):
        return safe_filename(self.paf.title)
