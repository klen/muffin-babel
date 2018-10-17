import muffin
import pytest


@pytest.fixture(scope='session')
def app():
    app = muffin.Application(
        'babel', PLUGINS=['muffin_jinja2', 'muffin_babel'],

        BABEL_CONFIGURE_JINJA2=True,
        BABEL_LOCALES_DIRS=['example/locales'],
    )

    @app.ps.babel.locale_selector
    def get_locale(request):
        return request.query.get('lang', 'en')

    @app.register('/')
    def index(request):
        return app.ps.babel.gettext('Hello World!')

    ls = app.ps.babel.lazy_gettext('Welcome!')

    @app.register('/lazy')
    def lazy(request):
        return str(ls)

    return app


async def test_translate(client):

    async with client.get('/', raise_for_status=True) as resp:
        text = await resp.text()
        assert 'Hello World!' in text

    async with client.get('/?lang=ru', raise_for_status=True) as resp:
        text = await resp.text()
        assert text == 'Привет, Мир!'

    async with client.get('/lazy', raise_for_status=True) as resp:
        text = await resp.text()
        assert text == 'Welcome!'

    async with client.get('/lazy?lang=ru', raise_for_status=True) as resp:
        text = await resp.text()
        assert text == 'Добро пожаловать!'
