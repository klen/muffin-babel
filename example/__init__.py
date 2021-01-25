"""Example application."""
import muffin
import muffin_jinja2
import muffin_babel


app = muffin.Application('babel', DEBUG=True)

jinja2 = muffin_jinja2.Plugin(app, template_folders=['example/templates'])
babel = muffin_babel.Plugin(app, locale_folders=['example/locales'])


@babel.locale_selector
async def get_locale(request, default='en'):
    """Return locale from GET lang param or automatically."""
    locale = request.query.get('lang')
    if not locale:
        return await muffin_babel.select_locale_by_request(request, default)
    return locale


@app.route('/')
async def index(request):
    """Localized Hello World."""
    return await jinja2.render(
        'base.html', message=babel.gettext('Hello World!'))
