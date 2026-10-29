from typing import TYPE_CHECKING

import muffin
import muffin_jinja2
import pytest
from asgi_babel import current_locale
from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo

import muffin_babel

if TYPE_CHECKING:
    from muffin_babel import Plugin as Babel


@pytest.fixture
def app():
    return muffin.Application(
        debug=True,
        babel_configure_jinja2=True,
        babel_locale_folders=["example/locales"],
    )


@pytest.fixture
def jinja2(app):
    return muffin_jinja2.Plugin(app)


@pytest.fixture
def babel(app):
    from muffin_babel import Plugin as Babel

    return Babel(app)


async def test_babel(app, jinja2, babel):
    await app.lifespan.run("startup")

    @app.route("/")
    async def index(request):
        assert babel.current_locale
        return babel.gettext("Hello World!")

    client = muffin.TestClient(app)

    res = await client.get(
        "/", headers={"accept-language": "ru-RU, ru;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5"}
    )
    assert await res.text() == "Привет, Мир!"

    @babel.locale_selector
    async def get_locale_from_request(request):
        return request.url.query.get("lang")

    res = await client.get("/")
    assert await res.text() == "Hello World!"

    res = await client.get("/?lang=ru")
    assert await res.text() == "Привет, Мир!"

    from jinja2 import Template

    template = Template("""{{ gettext('Hello World!') }}""")

    @app.route("/jinja")
    async def jinja(request):
        return await jinja2.render(template)

    res = await client.get("/jinja")
    assert await res.text() == "Hello World!"

    res = await client.get("/jinja?lang=ru")
    assert await res.text() == "Привет, Мир!"


async def test_babel_middleware(app, babel: "Babel"):
    @app.middleware
    async def process_locale(handler, scope, receive, send):
        # A correct locale has to be here
        assert babel.current_locale.language == "ru"
        return await handler(scope, receive, send)

    @app.route("/")
    async def index(request):
        assert babel.current_locale.language == "ru"
        return babel.gettext("Hello World!")

    await app.lifespan.run("startup")

    client = muffin.TestClient(app)

    async with client.lifespan():
        res = await client.get(
            "/", headers={"accept-language": "ru-RU, ru;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5"}
        )
        assert await res.text() == "Привет, Мир!"


def test_locale_ctx(babel: "Babel"):
    assert babel.gettext("Hello World!") == "Hello World!"

    with babel.locale_ctx("ru"):
        assert babel.gettext("Hello World!") == "Привет, Мир!"

    with babel.locale_ctx("en-RU"):
        assert babel.gettext("Hello World!") == "Hello World!"


def test_gettext(babel: "Babel"):
    assert babel.gettext("Hello %(user)s", user="John") == "Hello John"
    assert babel.gettext("Hello %(user)s") == "Hello %(user)s"


def test_ngettext(babel: "Babel"):
    assert babel.ngettext("%(num)s apple", "%(num)s apples", 2) == "2 apples"
    assert babel.ngettext("%(num)s apple", "%(num)s apples", 1) == "1 apple"
    assert babel.npgettext("fruit", "%(num)s apple", "%(num)s apples", 2) == "2 apples"


def test_pgettext(babel: "Babel"):
    # The example catalog has no contextual entries; the source string is returned
    assert babel.pgettext("greeting", "Hello World!") == "Hello World!"

    with babel.locale_ctx("ru"):
        assert babel.pgettext("greeting", "Hello World!") == "Hello World!"


def test_get_translations(babel: "Babel"):
    translations = babel.get_translations()
    assert translations.gettext("Hello World!") == "Hello World!"
    assert babel.get_translations() is translations


def test_current_locale(babel: "Babel"):
    babel.current_locale = "ru"
    assert babel.current_locale.language == "ru"
    assert babel.gettext("Hello World!") == "Привет, Мир!"

    # Unknown locales are ignored silently
    babel.current_locale = "unknown"
    assert babel.current_locale.language == "ru"

    babel.current_locale = "en"
    assert babel.gettext("Hello World!") == "Hello World!"


def test_setup_returns():
    from muffin_babel import Plugin

    assert Plugin().setup(muffin.Application("babel-setup")) is True


async def test_example():
    import example

    client = muffin.TestClient(example.app)

    async with client.lifespan():
        res = await client.get("/")
        assert "Hello World!" in await res.text()

        res = await client.get("/?lang=ru")
        assert "Привет, Мир!" in await res.text()


def test_default_locale_forms():
    # Both `en_US` and `en-US` are valid babel spellings, an unknown one falls back to English
    for value in ("en_US", "en-US", "unknown"):
        current_locale.set(None)  # other tests leave the locale of the context set
        plugin = muffin_babel.Plugin(
            muffin.Application("loc", babel_default_locale=value, babel_locale_folders=[])
        )
        assert plugin.current_locale.language == "en"


def test_get_translations_multiple_folders(tmp_path):
    # The example catalog lives in the first folder only; the empty folder must not break it
    plugin = muffin_babel.Plugin(
        muffin.Application("folders", babel_locale_folders=["example/locales", str(tmp_path)])
    )
    plugin.current_locale = "ru"
    assert plugin.gettext("Hello World!") == "Привет, Мир!"


def test_translations_are_not_shared_between_plugins(tmp_path):
    translated = muffin_babel.Plugin(
        muffin.Application("first", babel_locale_folders=["example/locales"])
    )
    translated.current_locale = "ru"
    assert translated.gettext("Hello World!") == "Привет, Мир!"

    empty = muffin_babel.Plugin(muffin.Application("second", babel_locale_folders=[str(tmp_path)]))
    empty.current_locale = "ru"
    assert empty.gettext("Hello World!") == "Hello World!"


def test_locale_ctx_restores_on_error(babel: "Babel"):
    babel.current_locale = "ru"

    with pytest.raises(RuntimeError), babel.locale_ctx("en"):
        raise RuntimeError

    assert babel.current_locale.language == "ru"


def test_gettext_keeps_unformattable_strings(babel: "Babel"):
    assert babel.gettext("50% off", user="John") == "50% off"
    assert babel.ngettext("50% off", "50% off", 2) == "50% off"


def test_region_locale(tmp_path):
    folder = tmp_path / "pt_BR" / "LC_MESSAGES"
    folder.mkdir(parents=True)
    catalog = Catalog(locale="pt_BR")
    catalog.add("Hello World!", "Ola Mundo!")
    with (folder / "messages.mo").open("wb") as mo:
        write_mo(mo, catalog)

    plugin = muffin_babel.Plugin(muffin.Application("region", babel_locale_folders=[str(tmp_path)]))
    plugin.current_locale = "pt-BR"
    assert plugin.gettext("Hello World!") == "Ola Mundo!"


def test_commands(tmp_path, capsys):
    (tmp_path / "src.py").write_text('gettext("Hello")\n')
    app = muffin.Application("cmds", babel_locale_folders=[str(tmp_path / "locales")])
    muffin_babel.Plugin(app)

    # Nothing to compile yet, this must not fail
    app.manage.run("babel-compile-messages")

    app.manage.run("babel-extract-messages", str(tmp_path))
    po_file = tmp_path / "locales" / "en" / "LC_MESSAGES" / "messages.po"
    assert po_file.exists()

    # A second extraction keeps the translations already in the catalog
    po_file.write_text(
        po_file.read_text().replace('msgid "Hello"\nmsgstr ""', 'msgid "Hello"\nmsgstr "Hi"')
    )
    app.manage.run("babel-extract-messages", str(tmp_path))
    assert 'msgstr "Hi"' in po_file.read_text()

    app.manage.run("babel-compile-messages")
    assert po_file.with_suffix(".mo").exists()

    app.manage.run("babel-export-csv")
    output = capsys.readouterr().out
    assert "Hello,Hi" in output
    assert "Project-Id-Version" not in output  # the catalog header is not a message
