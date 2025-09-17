# -*- coding: utf-8 -*-
# plex debugging
try:
    import plexhints  # noqa: F401
except ImportError:
    pass
else:  # the code is running outside of Plex
    from plexhints import plexhints_setup, update_sys_path
    plexhints_setup()  # reads the plugin plist file and determine if plexhints should use elevated policy or not
    update_sys_path()  # when running outside plex, append the path
    from plexhints.network_kit import HTTP  # network kit
    from plexhints.proxy_kit import Proxy  # proxy kit
    from audnexuslogging import Logging


import datetime
import json

class GraphicAudioMapper:
    def __init__(self, url, log, make_request):
        # type: (str, str, Logging, callable) -> None # type: ignore
        """
        Accepts a list of GraphicAudio JSON objects.
        """
        self.url = url
        self.log = log
        self.make_request = make_request
        self.objects = self.fetch_json()

    def fetch_json(self):
        """
        Fetch the JSON from the URL using make_request.
        """
        try:
            response = self.make_request(self.url, accept_json=True)
            if response:
                return json.loads(response)
            else:
                self.log.error("Failed to fetch JSON from both primary and backup URL")
                return []
        except Exception:
            self.log.debug("Failed to parse JSON")
            return []


    def parse_date(self, datestr):
        if not datestr:
            return None
        try:
            datestr = datestr.replace("Z", "")
            return datetime.datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%f")
        except Exception:
            self.log.debug("Failed to parse date")
            return None

    def find_by_isbn(self, isbn):
        for obj in self.objects:
            if obj.get("isbn") == isbn:
                return obj
        return None

    def apply_to_metadata(self, metadata, isbn):
        obj = self.find_by_isbn(isbn)
        if not obj:
            return False

        metadata.title = obj.get("title") or metadata.title
        metadata.summary = obj.get("description") or metadata.summary
        metadata.studio = "GraphicAudio"

        release_date = self.parse_date(obj.get("releaseDate"))
        if release_date:
            metadata.originally_available_at = release_date.date()

        # Genres
        metadata.genres.clear()
        genre = obj.get("genre")
        if genre:
            metadata.genres.add(genre)

        # Collections
        metadata.collections.clear()
        series_name = obj.get("seriesName")
        if series_name:
            metadata.collections.add(series_name)

        # Roles
        metadata.roles.clear()
        author = obj.get("author")
        if author:
            role = metadata.roles.new()
            role.role = "Author"
            role.tag = author

        cast = obj.get("cast", [])
        for actor in cast:
            role = metadata.roles.new()
            role.role = "Actor"
            role.tag = actor

        # Poster
        cover_url = obj.get("cover")
        if cover_url and cover_url not in metadata.posters:
            metadata.posters[cover_url] = Proxy.Media(self.make_request(cover_url, accept_json=False), sort_order=0)
            metadata.posters.validate_keys([cover_url])
        # Extra identifiers
        metadata.guid = obj.get("isbn") or obj.get("link")
        metadata.original_title = obj.get("subtitle")

        return True