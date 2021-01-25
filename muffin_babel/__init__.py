"""Muffin-Babel -- I18n engine for Muffin framework."""
import logging
import os
import typing as t
from numbers import Number

import muffin
from asgi_babel import current_locale, select_locale_by_request
from asgi_tools.types import Receive, Send
from babel import Locale, support
from babel.messages.extract import extract_from_dir
from babel.messages.frontend import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import write_po, read_po
from muffin.plugin import BasePlugin
from asgi_tools.utils import to_awaitable


__version__ = "0.5.2"
__project__ = "muffin-babel"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


F = t.TypeVar('F', bound=t.Callable[[muffin.Request, str], t.Coroutine[t.Any, t.Any, str]])

TRANSLATIONS: t.Dict[t.Tuple[str, str], support.Translations] = {}


class Plugin(BasePlugin):
    """The class is used to control the babel integration to Muffin application."""

    name = 'babel'
    defaults = {
        'auto_detect_locale': True,
        'configure_jinja2': True,       # install i18n support in muffin-jinja2
        'default_locale': 'en',         # default locale
        'domain': 'messages',           # default domain
        'locale_folders': ['locales'],    # where compiled locales are leaving
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

    def setup(self, app: muffin.Application, **options):  # noqa
        """Setup the plugin's commands."""
        super(Plugin, self).setup(app, **options)

        self.__locale_selector: t.Optional[t.Callable[[muffin.Request, str], t.Coroutine[t.Any, t.Any, str]]] = select_locale_by_request  # noqa

        # Install a middleware for autodetection
        if self.cfg.auto_detect_locale:
            app.middleware(self.__middleware__)

        @app.manage(lifespan=False)
        def babel_extract_messages(*dirnames: str, project: str = app.name, locations: bool = True,
                                   charset: str = 'utf-8', domain: str = self.cfg.domain,
                                   locale: str = self.cfg.default_locale):
            """Extract messages from source code.

            :param charset: charset to use in the output
            :param domain:  set domain name for locales
            :param project: set project name in output
            :param version: set project version in output
            :param locations: add message locations
            """
            Locale.parse(locale)

            dirs = [d for d in dirnames if os.path.isdir(d)]

            catalog = Catalog(locale=locale, project=project, charset=charset)
            for dname in dirs:
                for filename, lineno, message, comments, context in extract_from_dir(
                        dname, method_map=self.cfg.sources_map, options_map=self.cfg.options_map):

                    lines = []
                    if locations:
                        filepath = os.path.normpath(os.path.join(dname, filename))
                        lines = [(filepath, lineno)]

                    catalog.add(message, None, lines, auto_comments=comments, context=context)

            locales_dir = self.cfg.locale_folders[0]
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

        @app.manage(lifespan=False)
        def babel_compile_messages(use_fuzzy=False, statistics=False, domain=self.cfg.domain): # noqa
            """Compile messages for locales.

            :param domain:  set domain name for locales
            """
            for locales_dir in self.cfg.locale_folders:
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

    async def __middleware__(self, handler: t.Callable,
                             request: muffin.Request, receive: Receive, send: Send) -> t.Any:
        """Auto detect a locale by the given request."""
        await self.select_locale(request)
        return await handler(request, receive, send)

    async def startup(self):
        """Tune Jinja2 if the plugin is installed."""
        if self.cfg.configure_jinja2 and 'jinja2' in self.app.plugins:
            jinja2 = self.app.plugins['jinja2']
            jinja2.env.add_extension('jinja2.ext.i18n')
            jinja2.env.install_gettext_callables(
                lambda x: self.get_translations().ugettext(x),
                lambda s, p, n: self.get_translations().ungettext(s, p, n),
                newstyle=True
            )

    def locale_selector(self, fn: F) -> F:
        """Update self locale selector."""
        self.__locale_selector = to_awaitable(fn)
        return fn

    async def select_locale(self, request: muffin.Request):
        """Select a locale by the request."""
        if self.__locale_selector is None:
            return

        lang = await self.__locale_selector(request, self.cfg.default_locale)
        self.current_locale = lang

    @property
    def current_locale(self) -> Locale:
        """Get current locale."""
        locale = current_locale.get()
        if locale is None:
            self.current_locale = self.cfg.default_locale
            locale = current_locale.get()
        return locale

    @current_locale.setter
    def current_locale(self, lang: str):
        """Set current locale."""
        return current_locale.set(Locale.parse(lang))

    def get_translations(self, domain: str = None, locale: Locale = None) -> support.Translations:
        """Load and cache translations."""
        locale = locale or self.current_locale
        domain = domain or self.cfg.domain
        if (domain, locale.language) not in TRANSLATIONS:
            translations = None
            for path in reversed(self.cfg.locale_folders):
                trans = support.Translations.load(path, locales=locale, domain=domain)
                if translations:
                    translations._catalog.update(trans._catalog)
                else:
                    translations = trans

            TRANSLATIONS[(domain, locale.language)] = translations

        return TRANSLATIONS[(domain, locale.language)]

    def gettext(self, string: str, domain: str = None, **variables) -> str:
        """Translate a string with the current locale."""
        t = self.get_translations(domain)
        return t.ugettext(string) % variables

    def ngettext(
            self, singular: str, plural: str, num: Number, domain: str = None, **variables) -> str:
        """Translate a string wity the current locale.

        The `num` parameter is used to dispatch between singular and various plural forms of the
        message.

        """
        variables.setdefault('num', num)
        t = self.get_translations(domain)
        return t.ungettext(singular, plural, num) % variables

    def pgettext(self, context: str, string: str, domain: str = None, **variables) -> str:
        """Like :meth:`gettext` but with a context."""
        t = self.get_translations(domain)
        return t.upgettext(context, string) % variables

    def npgettext(
            self, context: str, singular: str, plural: str,
            num: Number, domain: str = None, **variables) -> str:
        """Like :meth:`ngettext` but with a context."""
        variables.setdefault('num', num)
        t = self.get_translations(domain)
        return t.unpgettext(context, singular, plural, num) % variables

#  pylama:ignore=W0212
