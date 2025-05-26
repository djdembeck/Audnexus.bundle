# -*- coding: utf-8 -*-
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TXXX, WXXX, ID3NoHeaderError
from mutagen.apev2 import APEv2, error as APEv2Error
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wavpack import WavPack
from urlparse import urlparse
from region_tools import available_regions


def get_tld_from_url(url):
    try:
        netloc = urlparse(url).netloc
        if netloc:
            parts = netloc.split('.')
            if len(parts) > 1:
                return '.' + parts[-1]
    except Exception:
        pass
    return None


def read_all_tags(filename):
    ext = os.path.splitext(filename)[1].lower()
    tags = {}

    if ext == '.mp3':
        # ID3
        try:
            audio = MP3(filename, ID3=ID3)
            for frame in audio.tags.values():
                if isinstance(frame, TXXX):
                    tags[frame.desc] = frame.text[0]
                elif isinstance(frame, WXXX):
                    tags[frame.desc] = frame.url
                elif hasattr(frame, 'text'):
                    tags[frame.FrameID] = frame.text[0]
                elif hasattr(frame, 'url'):
                    tags[frame.FrameID] = frame.url
                else:
                    tags[frame.FrameID] = str(frame)
        except ID3NoHeaderError:
            pass

        # APEv2
        try:
            ape = APEv2(filename)
            for key in ape.keys():
                value = ape[key]
                tags[key] = value[0] if isinstance(value, list) else value
        except APEv2Error:
            pass

    elif ext in ['.m4a', '.m4b']:
        audio = MP4(filename)
        for key, value in audio.tags.items():
            if key.startswith('----:com.apple.iTunes:'):
                tag_name = key.split(':')[-1]
                tags[tag_name] = value[0]
            else:
                tags[key] = value[0] if isinstance(value, list) else value

    elif ext == '.flac':
        audio = FLAC(filename)
        for key in audio.tags.keys():
            tags[key] = audio.tags[key][0]
        # APEv2
        try:
            ape = APEv2(filename)
            for key in ape.keys():
                value = ape[key]
                tags[key] = value[0] if isinstance(value, list) else value
        except APEv2Error:
            pass

    elif ext == '.ogg':
        audio = OggVorbis(filename)
        for key in audio.tags.keys():
            tags[key] = audio.tags[key][0]

    elif ext == '.opus':
        audio = OggOpus(filename)
        for key in audio.tags.keys():
            tags[key] = audio.tags[key][0]

    elif ext == '.wv':
        audio = WavPack(filename)
        for key in audio.tags.keys():
            tags[key] = audio.tags[key][0]

    tags = {k.upper(): v for k, v in tags.items()}
    return tags


def read_asin_tag(filename):
    tags = read_all_tags(filename)
    asin = tags.get('ASIN')
    if asin:
        return str(asin)
    else:
        return None


def read_region_tag(filename):
    tags = read_all_tags(filename)
    asin = get_tld_from_url(tags.get('WWWAUDIOFILE'))
    if asin:
        return str(asin).replace('.', '')
    else:
        return None


def get_region_by_tld(tld, default='us'):
    for region, data in available_regions.items():
        if data['TLD'] == tld:
            return region
    return default


def build_region_asin(filename, default_region='us'):
    asin = read_asin_tag(filename)
    region = get_region_by_tld(read_region_tag(filename), default_region)
    if not asin:
        return None
    return asin + "_" + region if region else asin
