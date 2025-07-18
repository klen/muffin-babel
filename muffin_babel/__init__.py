"""Muffin-Babel -- I18n engine for Muffin framework."""

import csv
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, ClassVar, TypeVar

from asgi_babel import current_locale, select_locale_by_request
from babel import Locale, UnknownLocaleError, support
from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from muffin import Application, Request
from muffin.plugins import BasePlugin

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

if TYPE_CHECKING:
    from asgi_tools.types import TASGIReceive, TASGISend

TLocaleSelector = Callable[[Request], Awaitable[str | None]]
TVLocaleSelector = TypeVar("TVLocaleSelector", bound=TLocaleSelector)

TRANSLATIONS: dict[tuple[str, str], support.Translations] = {}


class Plugin(BasePlugin):
    """The class is used to control the babel integration to Muffin application."""

    name = "babel"
    defaults: ClassVar = {
        "auto_detect_locale": True,
        "configure_jinja2": True,  # install i18n support in muffin-jinja2
        "default_locale": "en",  # default locale
        "domain": "messages",  # default domain
        "locale_folders": ["locales"],  # where compiled locales are leaving
        "sources_map": [
            ("**.py", "python"),
            ("**.html", "jinja2"),
        ],
        "options_map": {"**.html": {"encoding": "utf-8"}},
    }

    def setup(self, app: Application, **options):  # noqa: C901
        """Setup the plugin's commands."""
        super(Plugin, self).setup(app, **options)
        self.domain = self.cfg.domain

        self.__locale_selector: Callable[[Request], Awaitable[str | None]] = (
            select_locale_by_request
        )

        # Install a middleware for autodetection
        if self.cfg.auto_detect_locale:
            app.middleware(self.__middleware__, insert_first=True)

        @app.manage(lifespan=False)
        def babel_extract_messages(
            *dirnames: str,
            project: str = app.cfg.name,
            domain: str = self.domain,
            locations: bool = True,
            charset: str = "utf-8",
            locale: str = self.cfg.default_locale,
        ):
            """Extract messages from source code.

            :param charset: charset to use in the output
            :param domain:  set domain name for locales
            :param project: set project name in output
            :param version: set project version in output
            :param locations: add message locations
            """
            paths = [Path(d) for d in dirnames]
            dirs = [path for path in paths if path.is_dir()]

            catalog = Catalog(locale=locale, project=project, charset=charset)
            for dpath in dirs:
                for filename, lineno, message, comments, context in extract_from_dir(
                    dpath,
                    method_map=self.cfg.sources_map,
                    options_map=self.cfg.options_map,
                ):
                    lines = []
                    if locations:
                        filepath = dpath.absolute() / filename
                        lines = [(filepath.as_posix(), lineno)]

                    catalog.add(
                        message,
                        None,
                        lines,
                        auto_comments=comments,
                        context=context,
                    )

            locales_dir = Path(self.cfg.locale_folders[0])
            output = locales_dir / locale / "LC_MESSAGES" / f"{domain}.po"

            if output.exists():
                with output.open("rb") as f:
                    template = read_po(f, locale=locale, charset=charset)
                    template.update(catalog)
                    catalog = template

            if not output.parent.exists():
                output.parent.mkdir(parents=True)

            logger.info("writing PO template file to %s", output)
            with output.open("wb") as f:
                write_po(f, catalog, sort_output=not locations, sort_by_file=locations)

        @app.manage(lifespan=False)
        def babel_compile_messages(*, use_fuzzy=False, domain=self.domain):
            """Compile messages for locales.

            :param domain:  set domain name for locales
            """
            for locales_dir in self.cfg.locale_folders:
                source = Path(locales_dir)
                for locale in source.iterdir():
                    po_file = locale / "LC_MESSAGES" / f"{domain}.po"
                    if not po_file.exists():
                        continue

                    with po_file.open("rb") as po:
                        catalog = read_po(po, locale.name)

                    mo_file = po_file.with_suffix(".mo")

                    with mo_file.open("wb") as mo:
                        logger.info("writing MO template file to %s", mo_file)
                        write_mo(mo, catalog, use_fuzzy=use_fuzzy)

        @app.manage(lifespan=False)
        def babel_export_csv(*, domain: str = self.domain, locale: str = self.cfg.default_locale):
            """Export messages from a PO files as CSV."""
            writer = csv.writer(sys.stdout)
            writer.writerow(["id", "string", "context", "comment"])
            for locales_dir in self.cfg.locale_folders:
                po_file = Path(locales_dir) / locale / "LC_MESSAGES" / f"{domain}.po"
                if not po_file.exists():
                    continue

                with po_file.open("rb") as po:
                    catalog = read_po(po, locale)

                for message in catalog:
                    writer.writerow(
                        [
                            message.id,
                            message.string,
                            message.context,
                            "\n".join(message.auto_comments),
                        ]
                    )

    async def __middleware__(
        self, handler: Callable, request: Request, receive: "TASGIReceive", send: "TASGISend"
    ) -> Any:
        """Auto detect a locale by the given request."""
        lang = await self.__locale_selector(request)
        self.current_locale = lang or self.cfg.default_locale  # type: ignore[assignment]
        return await handler(request, receive, send)

    async def startup(self):
        """Tune Jinja2 if the plugin is installed."""
        if self.cfg.configure_jinja2 and "jinja2" in self.app.plugins:
            jinja2 = self.app.plugins["jinja2"]
            env = jinja2.env  # type: ignore[]
            env.add_extension("jinja2.ext.i18n")
            env.install_gettext_callables(
                lambda x: self.get_translations().ugettext(x),
                lambda s, p, n: self.get_translations().ungettext(s, p, n),
                newstyle=True,
            )

    def locale_selector(self, fn: TVLocaleSelector) -> TVLocaleSelector:
        """Update self locale selector."""
        self.__locale_selector = fn
        return fn

    @property
    def current_locale(self) -> Locale:
        """Get current locale."""
        locale = current_locale.get()
        if locale is None:
            locale = Locale.parse(self.cfg.default_locale, sep="-")
            current_locale.set(locale)
        return locale

    @current_locale.setter
    def current_locale(self, lang: str):
        """Set current locale."""
        try:
            locale = Locale.parse(lang, sep="-")
            return current_locale.set(locale)
        except (UnknownLocaleError, ValueError):
            return

    @contextmanager
    def locale_ctx(self, lang: str):
        """Update current locale as context manager."""
        old_locale = current_locale.get()
        self.current_locale = lang  # type: ignore[assignment]
        yield self
        current_locale.set(old_locale)

    def get_translations(
        self, domain: str | None = None, locale: Locale | None = None
    ) -> support.Translations:
        """Load and cache translations."""
        locale = locale or self.current_locale
        domain = domain or self.domain
        assert domain
        if (domain, locale.language) not in TRANSLATIONS:
            translations = None
            for path in reversed(self.cfg.locale_folders):
                trans = support.Translations.load(path, locales=locale.language, domain=domain)
                if translations:
                    translations.add(trans)  # type: ignore[attr-defined]
                else:
                    translations = trans

            TRANSLATIONS[(domain, locale.language)] = translations  # type: ignore[assignment]

        return TRANSLATIONS[(domain, locale.language)]

    def gettext(self, string: str, domain: str | None = None, **variables) -> str:
        """Translate a string with the current locale."""
        t = self.get_translations(domain)
        return render(t.ugettext(string), variables)

    def ngettext(
        self, singular: str, plural: str, num: int, domain: str | None = None, **variables
    ) -> str:
        """Translate a string wity the current locale.

        The `num` parameter is used to dispatch between singular and various plural forms of the
        message.

        """
        variables.setdefault("num", num)
        t = self.get_translations(domain)
        return t.ungettext(singular, plural, num) % variables

    def pgettext(self, context: str, string: str, domain: str | None = None, **variables) -> str:
        """Like :meth:`gettext` but with a context."""
        t = self.get_translations(domain)
        return render(t.upgettext(context, string), variables)

    def npgettext(
        self,
        context: str,
        singular: str,
        plural: str,
        num: int,
        domain: str | None = None,
        **variables,
    ) -> str:
        """Like :meth:`ngettext` but with a context."""
        variables.setdefault("num", num)
        t = self.get_translations(domain)
        return t.unpgettext(context, singular, plural, num) % variables


def render(value: str, variables) -> str:
    """Render a string with variables."""
    try:
        return value % variables if variables else value
    except KeyError as e:
        logger.warning("Missing variable for translation: %s", e)
        return value
