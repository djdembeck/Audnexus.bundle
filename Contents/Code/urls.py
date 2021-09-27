from logging import Logging

# Setup logger
log = Logging()


class SiteUrl:
    intl_sites = {
        'en': {
            'url': 'www.audible.com',
            'urltitle': u'title=',
            'rel_date': u'Release date',
            'nar_by': u'Narrated By',
            'nar_by2': u'Narrated by'
        },
        'fr': {
            'url': 'www.audible.fr',
            'urltitle': u'title=',
            'rel_date': u'Date de publication',
            'nar_by': u'Narrateur(s)',
            'nar_by2': u'Lu par'
        },
        'de': {
            'url': 'www.audible.de',
            'urltitle': u'title=',
            'rel_date': u'Erscheinungsdatum',
            'nar_by': u'Gesprochen von',
            'rel_date2': u'Veröffentlicht'
        },
        'it': {
            'url': 'www.audible.it',
            'urltitle': u'title=',
            'rel_date': u'Data di Pubblicazione',
            'nar_by': u'Narratore'
        },
    }

    sites_langs = {
        'www.audible.com': {'lang': 'en'},
        'www.audible.ca': {'lang': 'en'},
        'www.audible.co.uk': {'lang': 'en'},
        'www.audible.com.au': {'lang': 'en'},
        'www.audible.fr': {'lang': 'fr'},
        'www.audible.de': {'lang': 'de'},
        'www.audible.it': {'lang': 'it'},
    }

    def __init__(self, sitetype, base, lang='en'):
        self.sitetype = sitetype
        self.base = base
        self.lang = lang

    def set_context_urls(self):
        AUD_BASE_URL = 'https://' + str(self.base) + '/'
        AUD_TITLE_URL = self.urlsearchtitle

        AUD_BOOK_INFO_ARR = [
            AUD_BASE_URL,
            'pd/%s?ipRedirectOverride=true',
        ]
        self.context['AUD_BOOK_INFO'] = ''.join(
            AUD_BOOK_INFO_ARR
        )

        AUD_ARTIST_SEARCH_URL_ARR = [
            AUD_BASE_URL,
            'search?searchAuthor=%s&ipRedirectOverride=true',
        ]
        self.context['AUD_ARTIST_SEARCH_URL'] = ''.join(
            AUD_ARTIST_SEARCH_URL_ARR
        )

        AUD_ALBUM_SEARCH_URL_ARR = [
            AUD_BASE_URL,
            'search?',
            AUD_TITLE_URL,
            '%s&x=41&ipRedirectOverride=true',
        ]
        self.context['AUD_ALBUM_SEARCH_URL'] = ''.join(
            AUD_ALBUM_SEARCH_URL_ARR
        )

        AUD_KEYWORD_SEARCH_URL_ARR = [
            AUD_BASE_URL,
            ('search?filterby=field-keywords&advsearchKeywords=%s'
                '&x=41&ipRedirectOverride=true'),
        ]
        self.context['AUD_KEYWORD_SEARCH_URL'] = ''.join(
            AUD_KEYWORD_SEARCH_URL_ARR
        )

        AUD_SEARCH_URL_ARR = [
            AUD_BASE_URL,
            'search?',
            AUD_TITLE_URL,
            '{0}&searchAuthor={1}&x=41&ipRedirectOverride=true',
        ]
        self.context['AUD_SEARCH_URL'] = ''.join(AUD_SEARCH_URL_ARR)

    def base_is_manual(self):
        if self.base in self.sites_langs:
            log.debug('Pulling language from sites array')
            self.lang = self.sites_langs[self.base]['lang']
            if self.lang in self.intl_sites:
                self.base = self.intl_sites[self.lang]['url']
                self.urlsearchtitle = (
                    self.intl_sites[self.lang]['urltitle']
                )
                self.context['REL_DATE'] = (
                    self.intl_sites[self.lang]['rel_date']
                )
                self.context['NAR_BY'] = (
                    self.intl_sites[self.lang]['nar_by']
                )
                if 'rel_date2' in self.intl_sites[self.lang]:
                    self.context['REL_DATE_INFO'] = (
                        self.intl_sites[self.lang]['rel_date2']
                    )
                else:
                    self.context['REL_DATE_INFO'] = (
                        self.context['REL_DATE']
                    )
                if 'nar_by2' in self.intl_sites[self.lang]:
                    self.context['NAR_BY_INFO'] = (
                        self.intl_sites[self.lang]['nar_by2']
                    )
                else:
                    self.context['NAR_BY_INFO'] = self.context['NAR_BY']
            else:
                self.context['REL_DATE'] = 'Release date'
                self.context['REL_DATE_INFO'] = self.context['REL_DATE']
                self.context['NAR_BY'] = 'Narrated By'
                self.context['NAR_BY_INFO'] = 'Narrated by'

        # Log translations of certain terms
        log.separator(msg='LANG DEBUGGING', log_level="debug")
        data_to_log = [
            {'Sites language is': self.lang},
            {'REL_DATE': self.context['REL_DATE']},
            {'REL_DATE_INFO': self.context['REL_DATE_INFO']},
            {'NAR_BY date': self.context['NAR_BY']},
            {'NAR_BY_INFO': self.context['NAR_BY_INFO']},
        ]
        log.metadata(data_to_log, log_level="debug")
        log.separator(log_level="debug")

    def base_is_auto(self):
        log.debug(
            'Audible site will be chosen by library language'
            )
        log.debug(
            'Library Language is %s', self.lang
            )
        if self.base is None:
            self.base = 'www.audible.com'
        if self.lang in self.intl_sites:
            self.base = self.intl_sites[self.lang]['url']
            self.urlsearchtitle = self.intl_sites[self.lang]['urltitle']
            self.context['REL_DATE'] = (
                self.intl_sites[self.lang]['rel_date']
            )
            self.context['NAR_BY'] = self.intl_sites[self.lang]['nar_by']
            if 'rel_date2' in self.intl_sites[self.lang]:
                self.context['REL_DATE_INFO'] = (
                    self.intl_sites[self.lang]['rel_date2']
                )
            else:
                self.context['REL_DATE_INFO'] = (
                    self.context['REL_DATE']
                )
            if 'nar_by2' in self.intl_sites[self.lang]:
                self.context['NAR_BY_INFO'] = (
                    self.intl_sites[self.lang]['nar_by2']
                )
            else:
                self.context['NAR_BY_INFO'] = self.context['NAR_BY']
        else:
            self.context['REL_DATE'] = 'Release date'
            self.context['REL_DATE_INFO'] = self.context['REL_DATE']
            self.context['NAR_BY'] = 'Narrated By'
            self.context['NAR_BY_INFO'] = 'Narrated by'

    def SetupUrls(self):
        log.debug('Library/Search language is : %s', self.lang)
        self.context = {}
        if self.sitetype:
            log.debug('Manual Site Selection Enabled : %s', self.base)
            log.debug('Language being ignored due to manual site selection')
            self.base_is_manual()
        else:
            self.base_is_auto()

        self.set_context_urls()

        return self.context
