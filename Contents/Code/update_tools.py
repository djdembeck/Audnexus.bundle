# Import internal tools
from logging import Logging

# Setup logger
log = Logging()


class UpdateTool:
    def __init__(self, force, lang, media, metadata, url):
        self.date = None
        self.force = force
        self.genre_child = None
        self.genre_parent = None
        self.lang = lang
        self.media = media
        self.metadata = metadata
        self.rating = None
        self.series = ''
        self.series2 = ''
        self.url = url
        self.volume = ''
        self.volume2 = ''

    def re_parse_with_date_published(self, json_data):
        for data in json_data:
            if 'datePublished' in data:
                self.date = data['datePublished']
                self.title = data['name']
                self.thumb = data['image']
                # Set rating when available
                if 'aggregateRating' in data:
                    self.rating = (
                        data['aggregateRating']['ratingValue']
                    )
                author_array = []
                for c in data['author']:
                    author_array.append(c['name'])
                self.author = ",".join(author_array)

                narrator_array = []
                if 'readBy' in data:
                    for c in data['readBy']:
                        narrator_array.append(c['name'])
                else:
                    log.warn("No narrator listed for: " + self.metadata.id)
                    narrator_array.append("[Unknown Artist]")
                self.narrator = ",".join(narrator_array)
                self.studio = data['publisher']
                self.synopsis = data['description']
            if 'itemListElement' in data:
                self.genre_parent = (
                    data['itemListElement'][1]['item']['name']
                )
                try:
                    self.genre_child = (
                        data['itemListElement'][2]['item']['name']
                    )
                except AttributeError:
                    continue
                except IndexError:
                    log.warn(
                        '"' + self.title + '", '
                        "only has one genre"
                        )
                    continue

    # Writes metadata information to log.
    def writeInfo(self):
        log.separator(msg='New data', log_level="info")

        # Log basic metadata
        data_to_log = [
            {'ID': self.metadata.id},
            {'URL': self.url},
            {'Title': self.metadata.title},
            {'Release date': str(self.metadata.originally_available_at)},
            {'Studio': self.metadata.studio},
            {'Summary': self.metadata.summary},
            {'Poster URL': self.thumb},
        ]
        log.metadata(data_to_log, log_level="info")

        # Log basic metadata stored in arrays
        multi_arr = [
            {'Genres': self.metadata.genres},
            {'Moods(Authors)': self.metadata.moods},
            {'Styles(Narrators)': self.metadata.styles},
        ]
        log.metadata_arrs(multi_arr, log_level="info")

        log.separator(log_level="info")
