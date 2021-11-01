#! /usr/bin/python3
"""Valokuvakokoelma is Finnish for Photo Collection."""
# pylint: disable=line-too-long
import hashlib
import json
import pathlib
import sys

BUFFER_BYTES = 2 << 15
ENCODING = 'utf-8'

DB_OUT_ROOT = pathlib.Path.home() / 'Pictures' / 'describe'
KINDS = {
    'CLONE': 'clone',
    'LIVTO': 'livto',
    'PHOTO': 'photo',
    'VIDEO': 'video',
}


def sha256sum(path: pathlib.Path) -> str:
    """Calculate the SHA256 hash for content at path."""
    with open(path, "rb") as in_file:
        content_hash = hashlib.sha256()
        for byte_block in iter(lambda in_f=in_file: in_f.read(BUFFER_BYTES), b""):
            content_hash.update(byte_block)
        return content_hash.hexdigest()


def hash_to_path(kind: str, rep: str) -> pathlib.Path:
    """Derive path from content rep hash and create any folder required."""
    if kind not in KINDS.values():
        raise ValueError(f'unknown {kind=} for {rep=}')
    folder = DB_OUT_ROOT / kind / rep[:2]
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f'{rep}.json'


class Labels:
    """yes"""

    def __init__(self):
        """or"""
        self.to_refs = {}

    def update(self, refs, labels):
        """no"""
        if labels and refs:
            for label in labels:
                if label not in self.to_refs:
                    self.to_refs[label] = []
                for ref in refs:
                    if ref not in self.to_refs[label]:
                        self.to_refs[label].append(ref)

    def dump(self, path: pathlib.Path):
        """never"""
        self.to_refs = {k: self.to_refs[k] for k in sorted(self.to_refs)}
        for label in self.to_refs.keys():
            self.to_refs[label].sort()
        with open(path, 'wt', encoding=ENCODING) as labels_handle:
            json.dump(self.to_refs, labels_handle, indent=2)


class Medium:
    """Wrap it."""

    def __init__(self, ndx: int, media_entry, labels: Labels):
        """From dict."""
        self.medium = media_entry
        self.ndx = ndx
        self.is_photo = self.medium.get('isphoto', None)
        self.is_video = self.medium.get('ismovie', None)
        self.is_screenshot = self.medium.get('screenshot', None)
        self.species = None
        self.is_missing = self.medium.get('ismissing', None)
        self.is_cloudasset = self.medium.get('iscloudasset', None)

        self.path_str = self.medium.get('path', '')
        self.path_live_photo = self.medium.get('path_live_photo', '')

        self.path_to_medium = ''
        self.path_to_secondary = ''

        self.error = False
        self.error_detail = ''
        self.messages = []

        self.path_to_medium = ''
        self.path_to_secondary = ''
        self.content_rep = ''
        self.live_rep = ''

        self.refs = []

        self._validate()
        if not self.error:
            self._hash_content()

            if self.content_rep:
                self.refs.append(f'{self.species}:{self.content_rep[:2]}/{self.content_rep}')
            if self.live_rep:
                self.refs.append(f'{KINDS["LIVTO"]}:{self.live_rep[:2]}/{self.live_rep}')
            labels.update(self.refs, self.medium.get('labels', []))

    def validate(self):
        """Any chances?"""
        self._validate()
        if self.error:
            raise ValueError(self.error_detail)

    def dump(self):
        """Do it."""
        self._dump()
        if self.error:
            raise RuntimeError(self.error_detail)

    def _validate(self):
        """DRY."""
        if not self.is_photo and not self.is_video:
            self.error = True
            self.error_detail = f'{self.ndx=} is neither photo nor video'
            return

        self.species = KINDS['PHOTO'] if self.is_photo else KINDS['VIDEO']

        if self.is_screenshot:
            self.species = KINDS['CLONE']

        logic_attributes = (self.is_video, self.is_photo, self.is_screenshot, self.is_missing, self.is_cloudasset)
        if any(e is None for e in logic_attributes):
            self.messages.append(f'WARNING_META_NONE {self.ndx=}')

        if self.is_missing:
            if self.is_cloudasset:
                self.messages.append(f'OUT_OF_SYNC {self.ndx=}')
            else:
                self.messages.append(f'IS_MISSING {self.ndx=}')

        if not self.path_str:
            self.error = True
            self.error_detail = f'IGNORE_EMPTY_PATH {self.ndx=} {self.species=}'
            return

    def _hash_content(self):
        """YES"""
        self.path_to_medium = pathlib.Path(self.path_str)
        if not self.path_to_medium or not self.path_to_medium.is_file():
            self.error = True
            self.error_detail = f'path not found for entry no. {self.ndx}'
            return

        self.messages.append(f'{self.ndx=} {self.species=} points to {self.path_to_medium.name=}')

        if self.path_live_photo:
            self.path_to_secondary = pathlib.Path(self.path_live_photo)
            self.messages.append(f'::HAS_LIVE_NOVIE({self.path_to_secondary.name})')

        self.content_rep = sha256sum(self.path_to_medium)
        if not self.content_rep:
            self.error = True
            self.error_detail = 'no content rep'
            return

    def _hash_live(self):
        """YES"""
        if self.path_live_photo:
            self.live_rep = sha256sum(self.path_to_secondary)
            if not self.live_rep:
                self.error = True
                self.error_detail = 'no live rep'

    def _dump(self):
        """DRY."""
        self.messages.append(f'  -> {self.content_rep=}')
        with open(hash_to_path(self.species, self.content_rep), 'wt', encoding=ENCODING) as medium_handle:
            json.dump(self.medium, medium_handle, indent=2)

        if self.path_live_photo:
            self.messages.append(f'::{self.live_rep=}')
            with open(hash_to_path(KINDS['LIVTO'], self.live_rep), 'wt', encoding=ENCODING) as secondary_handle:
                json.dump(self.medium, secondary_handle, indent=2)



if len(sys.argv) != 2:
    print('valokuvakokoelma.py <photolibrarydump.json>')
    sys.exit(2)

db_dump_string = sys.argv[1].strip()
db_path = pathlib.Path(db_dump_string)

if not db_path or not db_path.is_file():
    print('photolibrarydump.json must be a file')
    sys.exit(1)

with open(db_path, 'rt', encoding=ENCODING) as handle:
    db = json.load(handle)

if not db:
    print('database empty')
    sys.exit(1)

media_count = len(db)
print(f'database with {media_count} media loaded')

labeling = Labels()
for number, thing in enumerate(db, start=1):

    try:
        medium = Medium(number, thing, labeling)
    except ValueError as val_err:
        print(val_err)
        print(''.join(medium.messages))
        continue

    try:
        medium.dump()
    except RuntimeError as run_err:
        print(run_err)

    print(''.join(medium.messages))


labeling.dump(pathlib.Path('labels.json'))

print('OK')
