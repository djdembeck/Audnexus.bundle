# Audiobooks (Audible)
# coding: utf-8
import json
import Queue
import re
# Import internal tools
from logging import Logging
from search_tools import SearchTool
from update_tools import UpdateTool
from urls import SiteUrl

VERSION_NO = '2021.09.26.1'

# Starting value for score before deductions are taken.
INITIAL_SCORE = 100
# Score required to short-circuit matching and stop searching.
GOOD_SCORE = 98
# Any score lower than this will be ignored.
IGNORE_SCORE = 45
# Audnexus is an API that aggregates audiobook data
audnexus_api_url = 'https://api.audnex.us/books/'

# Setup logger
log = Logging()


def ValidatePrefs():
    log.debug('ValidatePrefs function call')


def Start():
    HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = (
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0;'
        'SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729;'
        'Media Center PC 6.0'
    )
    HTTP.Headers['Accept-Encoding'] = 'gzip'
    log.separator(
        msg=(
            "Audible Audiobooks Agent v" + VERSION_NO
        ),
        log_level="info"
    )


class AudiobookArtist(Agent.Artist):
    name = 'Audiobooks'
    languages = [Locale.Language.English, 'de', 'fr', 'it']
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def getDateFromString(self, string):
        try:
            return Datetime.ParseDate(string).date()
        except AttributeError:
            return None

    def getStringContentFromXPath(self, source, query):
        return source.xpath('string(' + query + ')')

    def getAnchorUrlFromXPath(self, source, query):
        anchor = source.xpath(query)

        if not anchor:
            return None

        return anchor[0].get('href')

    def getImageUrlFromXPath(self, source, query):
        img = source.xpath(query)

        if not img:
            return None

        return img[0].get('src')

    def findDateInTitle(self, title):
        result = re.search(r'(\d+-\d+-\d+)', title)
        if result is not None:
            return Datetime.ParseDate(result.group(0)).date()
        return None

    def doSearch(self, ctx, url):
        html = HTML.ElementFromURL(url)
        found = []

        for r in html.xpath('//div[a/img[@class="yborder"]]'):
            date = self.getDateFromString(
                self.getStringContentFromXPath(r, 'text()[1]')
            )
            title = self.getStringContentFromXPath(r, 'a[2]')
            murl = self.getAnchorUrlFromXPath(r, 'a[2]')
            thumb = self.getImageUrlFromXPath(r, 'a/img')

            found.append(
                {'url': murl, 'title': title, 'date': date, 'thumb': thumb}
            )

        return found

    def search(self, results, media, lang, manual=False):
        # Author data is pulling from last.fm automatically.
        # This will probably never be built out unless a good
        # author source is identified.

        # Log some stuff
        log.separator(msg='ARTIST SEARCH', log_level='debug')
        log.debug(
            '* Album:           %s', media.album
        )
        log.debug(
            '* Artist:           %s', media.artist
        )
        log.warn(
            '****************************************'
            'Not Ready For Artist Search Yet'
            '****************************************'
        )
        log.separator(log_level='debug')

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try:
                    func(*args, **kargs)
                except Exception as e:
                    log.error(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))


class AudiobookAlbum(Agent.Album):
    name = 'Audiobooks'
    languages = [
        Locale.Language.English,
        'de',
        'fr',
        'it'
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
        url_info = SiteUrl(Prefs['sitetype'], Prefs['site'], lang)
        ctx = url_info.SetupUrls()

        # Instantiate search helper
        search_helper = SearchTool(lang, manual, media, results)

        search_helper.pre_search_logging()

        # Run helper before passing to SearchTool
        normalizedName = self.normalize_name(search_helper.media.album)
        # Strip title of things like unabridged and spaces
        search_helper.strip_title(normalizedName)
        # Validate author name
        search_helper.validate_author_name()
        # Generate search url
        searchUrl = self.create_search_url(ctx, search_helper)
        # Run actual search, and set the variable to it's return
        result = self.doSearch(ctx, searchUrl)

        # Write search result status to log
        if not result:
            log.warn(
                'No results found for query "%s"',
                normalizedName
            )
            return
        log.debug(
            'Found %s result(s) for query "%s"',
            len(result),
            normalizedName
        )

        info = self.run_search(search_helper, result)

        # Nested dict for localized separators
        # 'T_A' is the separator between title and author
        # 'A_N' is the separator between author and narrator
        separator_dict = {
            Locale.Language.English: {'T_A': 'by', 'A_N': 'w/'},
            'de': {'T_A': 'von', 'A_N': 'mit'},
            'fr': {'T_A': 'de', 'A_N': 'ac'},
            'it': {'T_A': 'di', 'A_N': 'con'}
        }
        local_separators = separator_dict[lang]
        log.debug(
            'Using localized separators "%s" and "%s"',
            local_separators['T_A'], local_separators['A_N'] 
        )

        # Output the final results.
        log.separator(log_level="debug")
        log.debug('Final result:')
        for i, r in enumerate(info):
            # Truncate long titles
            # Displayable chars is ~60 (see issue #32)
            # Inlcude tolerance to only truncate if >4 chars need to be cut
            title_trunc = (r['title'][:30] + '..') if len(
                r['title']) > 36 else r['title']

            # Shorten artist
            artist_initials = self.name_to_initials(r['artist'])
            # Shorten narrator
            narrator_initials = self.name_to_initials(r['narrator'])

            description = '\"%s\" %s %s %s %s' % (
                title_trunc,
                local_separators['T_A'],
                artist_initials, 
                local_separators['A_N'], 
                narrator_initials
            )
            log.debug(
                '  [%s]  %s. %s (%s) %s; %s {%s} [%s]',
                r['score'], (i + 1), r['title'], r['year'],
                r['artist'], r['narrator'], r['id'], r['thumb']
            )
            results.Append(
                MetadataSearchResult(
                    id=r['id'],
                    lang=lang,
                    name=description,
                    score=r['score'],
                    thumb=r['thumb'],
                    year=r['year']
                )
            )

            """
                If there are more than one result,
                and this one has a score that is >= GOOD SCORE,
                then ignore the rest of the results
            """
            if not manual and len(info) > 1 and r['score'] >= GOOD_SCORE:
                log.info(
                    '            *** The score for these results are great, '
                    'so we will use them, and ignore the rest. ***'
                )
                break

    def update(self, metadata, media, lang, force=False):
        url_info = SiteUrl(Prefs['sitetype'], Prefs['site'], lang)
        ctx = url_info.SetupUrls()

        log.separator(
            msg=(
                "UPDATING: " + media.title + (
                    " ID: " + metadata.id
                )
            ),
            log_level="info"
        )

        # Make url
        url = ctx['AUD_BOOK_INFO'] % metadata.id

        # Instantiate update helper
        update_helper = UpdateTool(force, lang, media, metadata, url)

        self.call_api(update_helper)

        # cleanup synopsis
        update_helper.synopsis = (
            update_helper.synopsis.replace("<i>", "")
            .replace("</i>", "")
            .replace("<em>", "")
            .replace("</em>", "")
            .replace("<u>", "")
            .replace("</u>", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("<strong>", "")
            .replace("</strong>", "")
            .replace("<ul>", "")
            .replace("</ul>", "\n")
            .replace("<ol>", "")
            .replace("</ol>", "\n")
            .replace("<li>", " • ")
            .replace("</li>", "\n")
            .replace("<br />", "")
            .replace("<p>", "")
            .replace("</p>", "\n")
        )

        # Handle single genre result
        if update_helper.genre_child:
            genre_string = (
                update_helper.genre_parent + ', ' + update_helper.genre_child
            )
        else:
            genre_string = update_helper.genre_parent

        # Setup logging of all data in the array
        data_to_log = [
            {'author': update_helper.author},
            {'date': update_helper.date},
            {'genres': genre_string},
            {'narrator': update_helper.narrator},
            {'rating': update_helper.rating},
            {'series': update_helper.series},
            {'series2': update_helper.series2},
            {'studio': update_helper.studio},
            {'synopsis': update_helper.synopsis},
            {'thumb': update_helper.thumb},
            {'title': update_helper.title},
        ]
        log.metadata(data_to_log, log_level="debug")

        self.compile_metadata(update_helper)

    """
        Search functions that require PMS imports,
        thus we cannot 'outsource' them to SearchTool
        Sorted by position in the search process
    """

    def normalize_name(self, input_name):
        # Normalize the name
        normalizedName = String.StripDiacritics(
            input_name
        )
        return normalizedName

    def name_to_initials(self, input_name):
        # Shorten input_name by splitting on whitespaces
        # Only the surname stays as whole, the rest gets truncated
        # and merged with dots.
        # Example: 'Arthur Conan Doyle' -> 'A.C.Doyle'
        name_parts = input_name.split()
        new_name = ""

        # Check if prename and surname exist, otherwise exit
        if len(name_parts) < 2:
            return input_name

        # traverse through prenames
        for i in range(len(name_parts)-1):
            s = name_parts[i]
            # If prename already is an initial take it as is
            new_name += (s[0] + '.') if len(s)>2 and s[1]!='.' else s
        # Add surname
        new_name += name_parts[-1]

        return new_name

    def create_search_url(self, ctx, helper):
        # Make the URL
        if helper.media.artist:
            searchUrl = ctx['AUD_SEARCH_URL'].format(
                (
                    String.Quote((helper.normalizedName).encode('utf-8'), usePlus=True)
                ),
                (
                    String.Quote((helper.media.artist).encode('utf-8'), usePlus=True)
                )
            )
        else:
            searchUrl = ctx['AUD_KEYWORD_SEARCH_URL'] % (
                String.Quote((helper.normalizedName).encode('utf-8'), usePlus=True)
            )
        return  searchUrl

    def doSearch(self, ctx, url):
        html = HTML.ElementFromURL(url)
        found = []

        # Set append to the returned array from this function
        found = self.before_xpath(ctx, found, html)

        return found

    def before_xpath(self, ctx, found, html):
        for r in html.xpath(
            '//ul//li[contains(@class,"productListItem")]'
        ):
            author = self.getStringContentFromXPath(
                r, (
                    'div/div/div/div/div/div/span/ul'
                    '/li[contains (@class,"authorLabel")]/span/a[1]'
                )
            )
            datetext = self.getStringContentFromXPath(
                r, (
                    u'div/div/div/div/div/div/span/ul/li'
                    '[contains (@class,"releaseDateLabel")]/span'
                    )
            )

            # Handle different date structures
            cleaned_datetext = re.search(r'\d{2}[-]\d{2}[-]\d{2}', datetext)
            if not cleaned_datetext:
                cleaned_datetext = re.search(r'\d{2}[.]\d{2}[.]\d{4}', datetext)

            date = self.getDateFromString(cleaned_datetext.group(0))
            language = self.getStringContentFromXPath(
                r, (
                    u'div/div/div/div/div/div/span/ul/li'
                    '[contains (@class,"languageLabel")]/span'
                    )
            ).split()[1]
            narrator = self.getStringContentFromXPath(
                r, (
                    u'div/div/div/div/div/div/span/ul/li'
                    '[contains (@class,"narratorLabel")]/span//a[1]'
                ).format(ctx['NAR_BY'])
            )
            murl = self.getAnchorUrlFromXPath(
                r, 'div/div/div/div/div/div/span/ul/li/h3//a[1]'
            )
            title = self.getStringContentFromXPath(
                r, (
                    'div/div/div/div/div/div/span/ul//a'
                    '[contains (@class,"bc-link")][1]'
                    )
            )
            thumb = self.getImageUrlFromXPath(
                r, 'div/div/div/div/div/div/div'
                '[contains(@class,"responsive-product-square")]/div/a/img'
            )
            log.separator(msg='XPATH SEARCH HIT', log_level="debug")

            found.append(
                {
                    'author': author,
                    'date': date,
                    'language': language,
                    'narrator': narrator,
                    'thumb': thumb,
                    'title': title,
                    'url': murl,
                }
            )
        return found

    def run_search(self, helper, result):
        # Walk the found items and gather extended information
        info = []

        log.separator(msg="Search results", log_level="info")
        for i, f in enumerate(result):
            valid_itemId = helper.get_id_from_url(item=f)
            if not valid_itemId:
                continue

            date = f['date']
            year = ''
            if date is not None:
                year = date.year

                # Make sure this isn't a pre-order listing
                if helper.check_if_preorder(date):
                    continue

            self.score_result(f, helper, i, info, valid_itemId, year)

            # Print separators for easy reading
            if i <= len(result):
                log.separator(log_level="info")

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)
        return info

    def score_result(self, f, helper, i, info, valid_itemId, year):
        author = f['author']
        date = f['date']
        language = f['language']
        narrator = f['narrator']
        thumb = f['thumb']
        title = f['title']

        # Array to hold score points for processing
        all_scores = []

        # Album name score
        title_score = self.score_album(helper, title)
        if title_score:
            all_scores.append(title_score)
        # Author name score
        author_score = self.score_author(author, helper)
        if author_score:
            all_scores.append(author_score)
        # Library language score
        lang_score = self.score_language(helper, language)
        if lang_score:
            all_scores.append(lang_score)

        # Because builtin sum() isn't available
        sum_scores=lambda numberlist:reduce(lambda x,y:x+y,numberlist,0)
        # Subtract difference from initial score
        score = INITIAL_SCORE - sum_scores(all_scores)

        log.info("Result #" + str(i + 1))
        # Log basic metadata
        data_to_log = [
            {'ID is': valid_itemId},
            {'Title is': title},
            {'Author is': author},
            {'Narrator is': narrator},
            {'Date is ': str(date)},
            {'Score is': str(score)},
            {'Thumb is': thumb},
        ]
        log.metadata(data_to_log, log_level="info")

        if score >= IGNORE_SCORE:
            info.append(
                {
                    'id': valid_itemId,
                    'title': title,
                    'year': year,
                    'date': date,
                    'score': score,
                    'thumb': thumb,
                    'artist': author,
                    'narrator': narrator
                }
            )
        else:
            log.info(
                '# Score is below ignore boundary (%s)... Skipping!',
                IGNORE_SCORE
            )

    def score_album(self, helper, title):
        """
            Compare the input album similarity to the search result album.
            Score is calculated with LevenshteinDistance
        """
        scorebase1 = helper.media.album
        scorebase2 = title.encode('utf-8')
        album_score = Util.LevenshteinDistance(
            scorebase1, scorebase2
        )
        log.debug("Score from album: " + str(album_score))
        return album_score

    def score_author(self, author, helper):
        """
            Compare the input author similarity to the search result author.
            Score is calculated with LevenshteinDistance
        """
        if helper.media.artist:
            scorebase3 = helper.media.artist
            scorebase4 = author
            author_score = Util.LevenshteinDistance(
                scorebase3, scorebase4
            )
            log.debug("Score from author: " + str(author_score))
            return author_score

    def score_language(self, helper, language):
        """
            Compare the library language to search results
            and knock off 2 points if they don't match.
        """
        lang_dict = {
            Locale.Language.English: 'English',
            'de': 'Deutsch',
            'fr': 'Français',
            'it': 'Italiano'
        }

        if language != lang_dict[helper.lang]:
            log.debug(
                'Audible language: %s; Library language: %s',
                language,
                helper.lang
            )
            log.debug("Book is not library language, deduct 2 points")
            return 2
        return 0

    """
        Update functions that require PMS imports,
        thus we cannot 'outsource' them to UpdateTool
        Sorted by position in the update process
    """

    def call_api(self, helper):
        request = str(HTTP.Request(audnexus_api_url + helper.metadata.id))
        response = json.loads(request)

        if 'authors' in response:
            helper.author = response['authors']
        if 'releaseDate' in response:
            helper.date = self.getDateFromString(response['releaseDate'])
        if 'genres' in response:
            for genre in response['genres']:
                if genre['type'] == 'parent':
                    helper.genre_parent = genre['name']
                else:
                    helper.genre_child = genre['name']
        if 'narrators' in response:
            helper.narrator = response['narrators']
        if 'rating' in response:
            helper.rating = response['rating']
        if 'seriesPrimary' in response:
            helper.series = response['seriesPrimary']['name']
            if 'position' in response['seriesPrimary']:
                helper.volume = response['seriesPrimary']['position']
        if 'seriesSecondary' in response:
            helper.series2 = response['seriesSecondary']['name']
            if 'position' in response['seriesSecondary']:
                helper.volume2 = response['seriesSecondary']['position']
        if 'publisherName' in response:
            helper.studio = response['publisherName']
        if 'summary' in response:
            helper.synopsis = response['summary']
        if 'image' in response:
            helper.thumb = response['image']
        if 'title' in response:
            helper.title = response['title']

    def compile_metadata(self, helper):
        # Set the date and year if found.
        if helper.date is not None:
            helper.metadata.originally_available_at = helper.date

        self.add_genres(helper)
        self.add_narrators_to_styles(helper)
        self.add_authors_to_moods(helper)
        self.add_series_to_moods(helper)

        # Other metadata
        helper.metadata.title = helper.title
        helper.metadata.title_sort = ' - '.join(
            filter(
                None, [(helper.series + ', ' + helper.volume), helper.title]
            )
        )
        helper.metadata.studio = helper.studio
        helper.metadata.summary = helper.synopsis

        if Prefs['cover_options'] == (
            "Use Audible cover"
        ):
            helper.metadata.posters[1] = Proxy.Media(
                HTTP.Request(helper.thumb)
            )
            helper.metadata.posters.validate_keys(helper.thumb)
        elif Prefs['cover_options'] == (
            "Download cover but don't overwrite existing"
        ):
            helper.metadata.posters[helper.thumb] = Proxy.Media(
                HTTP.Request(helper.thumb), sort_order=1
            )

        # Use rating only when available
        if helper.rating:
            helper.metadata.rating = float(helper.rating) * 2

        helper.writeInfo()

    def add_genres(self, helper):
        """
            Add genre(s) to Plex genres where available and depending on preference.
        """
        if not Prefs['no_overwrite_genre']:
            helper.metadata.genres.clear()
            helper.metadata.genres.add(helper.genre_parent)
            # Not all books have 2 genres
            if helper.genre_child:
                helper.metadata.genres.add(helper.genre_child)

    def add_narrators_to_styles(self, helper):
        """
            Adds narrators to styles.
        """
        helper.metadata.styles.clear()

        for narrator in helper.narrator:
            helper.metadata.styles.add(narrator['name'].strip())

    def add_authors_to_moods(self, helper):
        """
            Adds authors to moods, except for cases in contibutors list.
        """
        author_contributers_list = [
            'contributor',
            'translator',
            'foreword',
            'translated',
        ]
        helper.metadata.moods.clear()
        # Loop through authors to check if it has contributor wording
        for author in helper.author:
            if not [
                contrib for contrib in author_contributers_list if (
                    contrib in author['name'].lower()
                )
            ]:
                helper.metadata.moods.add(author['name'].strip())

    def add_series_to_moods(self, helper):
        """
            Adds book series' to moods, since collections are not supported
        """
        if helper.series:
            helper.metadata.moods.add("Series: " + helper.series)
        if helper.series2:
            helper.metadata.moods.add("Series: " + helper.series2)

    """
        General helper/repeated use functions
        Sorted alphabetically
    """

    def findDateInTitle(self, title):
        result = re.search(r'(\d+-\d+-\d+)', title)
        if result is not None:
            return Datetime.ParseDate(result.group(0)).date()
        return None

    def getDateFromString(self, string):
        try:
            return Datetime.ParseDate(string).date()
        except AttributeError:
            return None
        except ValueError:
            return None

    def getStringContentFromXPath(self, source, query):
        return source.xpath('string(' + query + ')')

    def getAnchorUrlFromXPath(self, source, query):
        anchor = source.xpath(query)

        if not anchor:
            return None

        return anchor[0].get('href')

    def getImageUrlFromXPath(self, source, query):
        img = source.xpath(query)

        if not img:
            return None

        return img[0].get('src')

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def json_decode(self, output):
        try:
            return json.loads(output, encoding="utf-8")
        except AttributeError:
            return None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

    """
        Queueing functions
    """

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try:
                    func(*args, **kargs)
                except Exception as e:
                    log.error(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))
