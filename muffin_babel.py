""" Muffin-Babel -- I18n engine for Muffin framework. """

import asyncio
import re
import os
import logging

from babel import Locale, support
from babel.messages.extract import extract_from_dir
from babel.messages.frontend import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import write_po, read_po
from muffin.plugins import BasePlugin
from muffin.utils import slocal
from speaklater import make_lazy_string


__version__ = "0.0.1"
__project__ = "muffin-babel"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

locale_delim_re = re.compile(r'[_-]')
accept_re = re.compile(
    r'''(                       # media-range capturing-parenthesis
              [^\s;,]+              # type/subtype
              (?:[ \t]*;[ \t]*      # ";"
                (?:                 # parameter non-capturing-parenthesis
                  [^\s;,q][^\s;,]*  # token that doesn't start with "q"
                |                   # or
                  q[^\s;,=][^\s;,]* # token that is more than just "q"
                )
              )*                    # zero or more parameters
            )                       # end of media-range
            (?:[ \t]*;[ \t]*q=      # weight is a "q" parameter
              (\d*(?:\.\d+)?)       # qvalue capturing-parentheses
              [^,]*                 # "extension" accept params: who cares?
            )?                      # accept params are optional
        ''', re.VERBOSE)


def parse_accept_header(header):
    """ Parse accept headers. """
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

    """ The class is used to control the babel integration to Muffin application. """

    name = 'babel'
    defaults = {
        'configure_jinja2': False,  # install i18n support in muffin-jinja2
        'default_locale': 'en',     # default locale
        'locales_dir': 'locales',   # where compiled locales are leaving
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
    locale_selector_func = None

    def setup(self, app):
        """ Setup the plugin's commands. """
        super(Plugin, self).setup(app)

        @app.manage.command
        def extract_messages(
                dirname, project='', version='', charset='utf-8', locale=self.cfg.default_locale):
            """ Extract messages from source code.

            :param charset: charset to use in the output
            :param output: write PO template file to destination
            :param project: set project name in output
            :param version: set project version in output

            """
            Locale.parse(locale)

            if not os.path.isdir(dirname):
                raise SystemExit('%r is not a directory' % dirname)

            catalog = Catalog(locale=locale, project=project, version=version, charset=charset)
            for filename, lineno, message, comments, context in extract_from_dir(
                    dirname, method_map=self.cfg.sources_map, options_map=self.cfg.options_map):
                filepath = os.path.normpath(os.path.join(dirname, filename))
                catalog.add(message, None, [(filepath, lineno)],
                            auto_comments=comments, context=context)

            output = os.path.join(
                self.cfg.locales_dir, locale, 'LC_MESSAGES', '%s.po' % self.app.name)

            if os.path.exists(output):
                with open(output, 'rb') as f:
                    template = read_po(f, locale=locale, charset=charset)
                    template.update(catalog)
                    catalog = template

            if not os.path.exists(os.path.dirname(output)):
                os.makedirs(os.path.dirname(output))

            logger.info('writing PO template file to %s' % output)
            outfile = open(output, 'wb')

            try:
                write_po(outfile, catalog, include_previous=True)
            finally:
                outfile.close()

        @app.manage.command
        def compile_messages(use_fuzzy=False, statistics=False):
            for locale in os.listdir(self.cfg.locales_dir):
                po_file = os.path.join(
                    self.cfg.locales_dir, locale, 'LC_MESSAGES', app.name + '.po')

                if not os.path.exists(po_file):
                    continue

                with open(po_file, 'r') as po:
                    catalog = read_po(po, locale)

                mo_file = os.path.join(
                    self.cfg.locales_dir, locale, 'LC_MESSAGES', app.name + '.mo')

                with open(mo_file, 'wb') as mo:
                    logger.info('writing MO template file to %s' % mo_file)
                    write_mo(mo, catalog, use_fuzzy=use_fuzzy)

    def start(self, app):
        """ Initialize a local namespace. """
        self.local = slocal(app.loop)
        if self.cfg.configure_jinja2 and 'jinja2' in app.ps:
            app.ps.jinja2.env.add_extension('jinja2.ext.i18n')
            app.ps.jinja2.env.install_gettext_callables(
                lambda x: self.get_translations().ugettext(x),
                lambda s, p, n: self.get_translations().ungettext(s, p, n),
                newstyle=True
            )

    @asyncio.coroutine
    def middleware_factory(self, app, handler):
        """ Set locale from request. """
        if not self.locale_selector_func:
            return handler

        @asyncio.coroutine
        def middleware(request):
            self.local.babel_locale = Locale.parse(self.locale_selector_func(request))
            return (yield from handler(request))

        return middleware

    def locale_selector(self, func):
        """ Initialize a locale selector function. """
        self.locale_selector_func = func

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
            for q, ulocale in ulocales:
                ulocale = locale_delim_re.split(ulocale)[0]
                if ulocale.lower() == locale.lower():
                    return ulocale

        return ulocales[0][1]

    def get_translations(self):
        """ Get current translations. """
        if self.local is None or not hasattr(self.local, 'babel_locale'):
            return support.NullTranslations()

        if not hasattr(self.local, 'babel_translations'):
            self.local.babel_translations = support.Translations.load(
                self.cfg.locales_dir, locales=self.local.babel_locale, domain=self.app.name)

        return self.local.babel_translations

    def gettext(self, string, **variables):
        """Translate a string with the current locale."""
        t = self.get_translations()
        return t.ugettext(string) % variables

    def ngettext(self, singular, plural, num, **variables):
        """Translate a string wity the current locale.

        The `num` parameter is used to dispatch between singular and various plural forms
        of the message.

        """
        variables.setdefault('num', num)
        t = self.get_translations()
        return t.ungettext(singular, plural, num) % variables

    def pgettext(self, context, string, **variables):
        """Like :meth:`gettext` but with a context."""
        t = self.get_translations()
        return t.upgettext(context, string) % variables

    def npgettext(self, context, singular, plural, num, **variables):
        """Like :meth:`ngettext` but with a context."""
        variables.setdefault('num', num)
        t = self.get_translations()
        return t.unpgettext(context, singular, plural, num) % variables

    def lazy_gettext(self, string, **variables):
        """Like :meth:`gettext` but the string returned is lazy."""
        return make_lazy_string(self.gettext, string, **variables)

    def lazy_pgettext(self, context, string, **variables):
        """Like :meth:`pgettext` but the string returned is lazy."""
        return make_lazy_string(self.pgettext, context, string, **variables)
