"""Muffin-Babel -- I18n engine for Muffin framework."""
import logging
import os
import re

from babel import Locale, support                   # noqa
from babel.messages.extract import extract_from_dir # noqa
from babel.messages.frontend import Catalog         # noqa
from babel.messages.mofile import write_mo          # noqa
from babel.messages.pofile import write_po, read_po # noqa
from muffin.plugins import BasePlugin
from muffin.utils import slocal
from speaklater import make_lazy_string             # noqa


__version__ = "0.4.5"
__project__ = "muffin-babel"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

locale_delim_re = re.compile(r'[_-]')
accept_re = re.compile(
    r'''(                         # media-range capturing-parenthesis
            [^\s;,]+              # type/subtype
            (?:[ \t]*;[ \t]*      # ";"
            (?:                   # parameter non-capturing-parenthesis
                [^\s;,q][^\s;,]*  # token that doesn't start with "q"
            |                     # or
                q[^\s;,=][^\s;,]* # token that is more than just "q"
            )
            )*                    # zero or more parameters
        )                         # end of media-range
        (?:[ \t]*;[ \t]*q=        # weight is a "q" parameter
            (\d*(?:\.\d+)?)       # qvalue capturing-parentheses
            [^,]*                 # "extension" accept params: who cares?
        )?                        # accept params are optional
    ''', re.VERBOSE)


def parse_accept_header(header):
    """Parse accept headers."""
    result = []
    for match in accept_re.finditer(header):
        quality = match.group(2)
        if not quality:
            quality = 1
        else:
            quality = max(min(float(quality), 1), 0)
        result.append((match.group(1), quality))
    return result


class Plugin(BasePlugin):
    """The class is used to control the babel integration to Muffin application."""

    name = 'babel'
    defaults = {
        'configure_jinja2': True,       # install i18n support in muffin-jinja2
        'default_locale': 'en',         # default locale
        'domain': 'messages',           # default domain (app.name)
        'locales_dirs': ['locales'],    # where compiled locales are leaving
        'sources_map': [
            ('**.py', 'python'),
            ('**.html', 'jinja2'),
        ],
        'options_map': {
            '**.html': {
                'encoding': 'utf-8'
            }
        }
    }

    local = None
    translations = {}
    locale_selector_func = None

    def setup(self, app):
        """Setup the plugin's commands."""
        super(Plugin, self).setup(app)
        if isinstance(self.cfg['locales_dirs'], str):
            self.cfg['locales_dirs'] = [self.cfg['locales_dirs']]

        @app.manage.command(init=False)
        def extract_messages(   # noqa
                *dirnames, project=app.name, version=app.cfg.get('VERSION', ''), locations=True,
                charset='utf-8', domain=self.cfg.domain, locale=self.cfg.default_locale):
            """Extract messages from source code.

            :param charset: charset to use in the output
            :param domain:  set domain name for locales
            :param project: set project name in output
            :param version: set project version in output
            :param locations: add message locations
            """
            Locale.parse(locale)

            dirnames = [d for d in dirnames if os.path.isdir(d)]

            catalog = Catalog(locale=locale, project=project, version=version, charset=charset)
            for dname in dirnames:
                for filename, lineno, message, comments, context in extract_from_dir(
                        dname, method_map=self.cfg.sources_map, options_map=self.cfg.options_map):

                    lines = []
                    if locations:
                        filepath = os.path.normpath(os.path.join(dname, filename))
                        lines = [(filepath, lineno)]

                    catalog.add(message, None, lines, auto_comments=comments, context=context)

            locales_dir = self.cfg.locales_dirs[0]
            output = os.path.join(locales_dir, locale, 'LC_MESSAGES', '%s.po' % domain)

            if os.path.exists(output):
                with open(output, 'rb') as f:
                    template = read_po(f, locale=locale, charset=charset)
                    template.update(catalog)
                    catalog = template

            if not os.path.exists(os.path.dirname(output)):
                os.makedirs(os.path.dirname(output))

            logger.info('writing PO template file to %s', output)
            outfile = open(output, 'wb')

            try:
                write_po(outfile, catalog, include_previous=True,
                         sort_output=not locations, sort_by_file=locations)
            finally:
                outfile.close()

        @app.manage.command(init=False)
        def compile_messages(use_fuzzy=False, statistics=False, domain=self.cfg.domain): # noqa
            """Compile messages for locales.

            :param domain:  set domain name for locales
            """
            for locales_dir in self.cfg.locales_dirs:
                for locale in os.listdir(locales_dir):
                    po_file = os.path.join(locales_dir, locale, 'LC_MESSAGES', domain + '.po')

                    if not os.path.exists(po_file):
                        continue

                    with open(po_file, 'r') as po:
                        catalog = read_po(po, locale)

                    mo_file = os.path.join(locales_dir, locale, 'LC_MESSAGES', domain + '.mo')

                    with open(mo_file, 'wb') as mo:
                        logger.info('writing MO template file to %s', mo_file)
                        write_mo(mo, catalog, use_fuzzy=use_fuzzy)

    async def startup(self, app):
        """Initialize a local namespace and setup Jinja2."""
        self.local = slocal(app.loop)
        if self.cfg.configure_jinja2 and 'jinja2' in app.ps:
            app.ps.jinja2.env.add_extension('jinja2.ext.i18n')
            app.ps.jinja2.env.install_gettext_callables(
                lambda x: self.get_translations().ugettext(x),
                lambda s, p, n: self.get_translations().ungettext(s, p, n),
                newstyle=True
            )

        if self.locale_selector_func:
            app.middlewares.append(self._middleware)

    async def _middleware(self, request, handler):
        locale = Locale.parse(self.locale_selector_func(request))
        self.locale = locale
        return await handler(request)

    _middleware.__middleware_version__ = 1

    def get_translations(self, domain=None, locale=None):
        """Load translations for given or configuration domain.

        :param domain: Messages domain (str)
        :param locale: Locale object
        """
        if locale is None:

            if self.locale is None:
                return support.NullTranslations()

            locale = self.locale

        if domain is None:
            domain = self.cfg.domain

        if (domain, locale.language) not in self.translations:
            translations = None
            for locales_dir in reversed(self.cfg.locales_dirs):
                trans = support.Translations.load(
                    locales_dir, locales=locale, domain=domain)
                if translations:
                    translations._catalog.update(trans._catalog)
                else:
                    translations = trans

            self.translations[(domain, locale.language)] = translations

        return self.translations[(domain, locale.language)]

    def locale_selector(self, func):
        """Initialize a locale selector function."""
        self.locale_selector_func = func

    @property
    def locale(self):
        """Return current locale."""
        return getattr(self.local, 'babel_locale', None)

    @locale.setter
    def locale(self, value):
        """Set current locale."""
        if not isinstance(value, Locale):
            value = Locale.parse(value)
        self.local.babel_locale = value

    def select_locale_by_request(self, request, locales=()):
        """Choose an user's locales by request."""
        default_locale = locales and locales[0] or self.cfg.default_locale

        if len(locales) == 1 or 'ACCEPT-LANGUAGE' not in request.headers:
            return default_locale

        ulocales = [
            (q, locale_delim_re.split(v)[0])
            for v, q in parse_accept_header(request.headers['ACCEPT-LANGUAGE'])
        ]
        ulocales.sort()
        ulocales.reverse()

        for locale in locales:
            for _, ulocale in ulocales:
                ulocale = locale_delim_re.split(ulocale)[0]
                if ulocale.lower() == locale.lower():
                    return ulocale

        return ulocales[0][1]

    def gettext(self, string, domain=None, **variables):
        """Translate a string with the current locale."""
        t = self.get_translations(domain)
        return t.ugettext(string) % variables

    def ngettext(self, singular, plural, num, domain=None, **variables):
        """Translate a string wity the current locale.

        The `num` parameter is used to dispatch between singular and various plural forms of the
        message.

        """
        variables.setdefault('num', num)
        t = self.get_translations(domain)
        return t.ungettext(singular, plural, num) % variables

    def pgettext(self, context, string, domain=None, **variables):
        """Like :meth:`gettext` but with a context."""
        t = self.get_translations(domain)
        return t.upgettext(context, string) % variables

    def npgettext(self, context, singular, plural, num, domain=None, **variables):
        """Like :meth:`ngettext` but with a context."""
        variables.setdefault('num', num)
        t = self.get_translations(domain)
        return t.unpgettext(context, singular, plural, num) % variables

    def lazy_gettext(self, *args, **kwargs):
        """Like :meth:`gettext` but the string returned is lazy."""
        return make_lazy_string(self.gettext, *args, **kwargs)

    def lazy_pgettext(self, *args, **kwargs):
        """Like :meth:`pgettext` but the string returned is lazy."""
        return make_lazy_string(self.pgettext, *args, **kwargs)

#  pylama:ignore=W0212
