import fnmatch
from glob import glob as _glob
import os
import unicodedata

from typing import Union

try:
    unicode
except NameError:
    unicode = str  # overwrite unicode for python3


def glob(pattern, recursive=False):
    # type: (Union[str, bytes], bool) -> list
    if not recursive:
        return _glob(pattern)

    # Split the pattern into the directory part and filename part
    dir_name, base_name = os.path.split(pattern)

    if not dir_name:
        dir_name = '.'

    matches = []
    for root, dir_names, filenames in os.walk(dir_name):
        for filename in fnmatch.filter(filenames, base_name):
            matches.append(os.path.join(root, filename))
    return matches


def makedirs(name, mode=0o777, exist_ok=False):
    # type: (Union[str, bytes], int, bool) -> None
    """Python 2 Compatibility for exist_ok argument in os.makedirs command. Added by python-plexapi-backport"""
    if not exist_ok and os.path.isdir(name):
        raise OSError("Directory '{}' already exists.".format(name))
    if not os.path.isdir(name):
        os.makedirs(name, mode=mode)


def unicodedata_normalize(form, input_string):
    # type: (Union[str, unicode], Union[str, unicode]) -> unicode
    if not isinstance(form, unicode):
        form = form.decode('utf-8')

    if not isinstance(input_string, unicode):
        input_string = input_string.decode('utf-8')

    return unicodedata.normalize(form, input_string)
