"""Example application."""
import os

import muffin


app = muffin.Application(
    'babel',

    PLUGINS=(
        'muffin_babel',
        'muffin_jinja2',
    ),

    JINJA2_TEMPLATE_FOLDERS=['example/templates'],

    BABEL_CONFIGURE_JINJA2=True,
    BABEL_LOCALES_DIRS=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')

)

_ = app.ps.babel.gettext


@app.ps.babel.locale_selector
def set_locale(request):
    """Return locale from GET lang param or automatically."""
    return request.query.get('lang', app.ps.babel.select_locale_by_request(request))


@app.register('/')
def index(request):
    """Localized Hello World."""
    return app.ps.jinja2.render('base.html', message=_('Hello World!'))
