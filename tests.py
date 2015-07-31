import muffin
import pytest


@pytest.fixture(scope='session')
def app(loop):
    app = muffin.Application(
        'babel', loop=loop,

        PLUGINS=['muffin_jinja2', 'muffin_babel'],

        BABEL_CONFIGURE_JINJA2=True,
        BABEL_LOCALES_DIRS=['example/locales'],
    )

    @app.ps.babel.locale_selector
    def get_locale(request):
        return request.GET.get('lang', 'en')

    return app


def test_translate(app, client):

    @app.register('/')
    def index(request):
        return app.ps.babel.gettext('Hello World!')

    response = client.get('/')
    assert 'Hello World!' in response.text

    response = client.get('/?lang=ru')
    assert response.text == 'Привет, Мир!'

    ls = app.ps.babel.lazy_gettext('Welcome!')

    @app.register('/lazy')
    def lazy(request):
        return ls

    response = client.get('/lazy?lang=ru')
    assert response.text == 'Добро пожаловать!'
