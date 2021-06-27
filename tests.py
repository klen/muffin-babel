import muffin
import muffin_jinja2


async def test_babel():
    from muffin_babel import Plugin as Babel

    app = muffin.Application(
        debug=True,
        babel_configure_jinja2=True,
        babel_locale_folders=['example/locales'],
    )
    jinja2 = muffin_jinja2.Plugin(app)
    babel = Babel(app)

    await app.lifespan.run('startup')

    @app.route('/')
    async def index(request):
        assert babel.current_locale
        return babel.gettext('Hello World!')

    client = muffin.TestClient(app)

    res = await client.get('/', headers={
        'accept-language': 'ru-RU, ru;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5'
    })
    assert await res.text() == 'Привет, Мир!'

    @babel.locale_selector
    async def get_locale_from_request(request):
        return request.url.query.get('lang')

    res = await client.get('/')
    assert await res.text() == 'Hello World!'

    res = await client.get('/?lang=ru')
    assert await res.text() == 'Привет, Мир!'

    from jinja2 import Template

    template = Template("""{{ gettext('Hello World!') }}""")

    @app.route('/jinja')
    async def jinja(request):
        return await jinja2.render(template)

    res = await client.get('/jinja')
    assert await res.text() == 'Hello World!'

    res = await client.get('/jinja?lang=ru')
    assert await res.text() == 'Привет, Мир!'


async def test_babel_middleware():
    from muffin_babel import Plugin as Babel

    app = muffin.Application(babel_locale_folders=['example/locales'])
    babel = Babel(app)

    @app.middleware
    async def process_locale(handler, scope, receive, send):
        # A correct locale has to be here
        assert babel.current_locale.language == 'ru'
        return await handler(scope, receive, send)

    @app.route('/')
    async def index(request):
        assert babel.current_locale.language == 'ru'
        return babel.gettext('Hello World!')

    await app.lifespan.run('startup')

    client = muffin.TestClient(app)

    async with client.lifespan():
        res = await client.get('/', headers={
            'accept-language': 'ru-RU, ru;q=0.9, en;q=0.8, de;q=0.7, *;q=0.5'
        })
        assert await res.text() == 'Привет, Мир!'
