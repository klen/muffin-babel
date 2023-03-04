Muffin-Babel
############

.. _description:

**Muffin-Babel** -- an extension to Muffin_ that adds localization support with help of Babel_.

.. _badges:

.. image:: https://github.com/klen/muffin-babel/workflows/tests/badge.svg
    :target: https://github.com/klen/muffin-babel/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/muffin-babel
    :target: https://pypi.org/project/muffin-babel/
    :alt: PYPI Version

.. image:: https://img.shields.io/pypi/pyversions/muffin-babel
    :target: https://pypi.org/project/muffin-babel/
    :alt: Python Versions

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.8

.. _installation:

Installation
=============

**Muffin-Babel** should be installed using pip: ::

    pip install muffin-babel

.. _usage:

Usage
=====

Initialize and setup the plugin:

.. code-block:: python

    import muffin
    import muffin_babel

    # Create Muffin Application
    app = muffin.Application('example')

    # Initialize the plugin
    # As alternative: babel = muffin_babel.Plugin(app, **options)
    babel = muffin_babel.Plugin()
    babel.setup(app, template_folders=['src/templates'])

    # Use it inside your handlers
    @app.route('/')
    async def index(request):
        # Get current locale
        assert babel.current_locale
        # Translate a text
        return babel.gettext('Hello World!')


Setup a locale selector function (by default the plugin is parsing ``accept-language`` header):

.. code-block:: python

    @babel.locale_selector
    async def get_locale(request):
        """ Return locale either from request.query or from request headers. """
        locale = request.query.get('lang')
        if not locale:
            return await muffin_babel.select_locale_by_request(request, default)
        return locale

Use `babel.gettext`, `babel.pgettext` callables in your code:

.. code-block:: python

    @app.route('/')
    def index(request):
        return babel.gettext('Hello!')


Jinja2
------

The `Muffin-Babel` has integration with `Muffin-Jinja2`, so if you have
`muffin_jinja2` plugin enabled, the plugin provides `gettext` and `ngettext`
function inside the Jinja2 templates' context.


Options
-------

========================== ============== ===============================================
 Name                      Default Value  Description
========================== ============== ===============================================
 **AUTO_DETECT_LOCALE**    ``True``       Installs a middleware to automatically detect users locales
 **CONFIGURE_JINJA2**      ``True``       Installs i18n support for jinja2 templates (through ``muffin-jinja``)
 **DEFAULT_LOCALE**        ``"en"``       Default locale
 **DOMAIN**                ``"messages"`` Default localization domain
 **SOURCES_MAP**                          Babel sources map
 **OPTIONS_MAP**                          Babel options map
========================== ============== ===============================================

You are able to provide the options when you are initiliazing the plugin:

.. code-block:: python

    babel.setup(app, default_locale='fr')


Or setup it inside ``Muffin.Application`` config using the ``BABEL_`` prefix:

.. code-block:: python

   BABEL_DEFAULT_LOCALE = 'fr'

``Muffin.Application`` configuration options are case insensitive

Commands
========

The plugin adds two commands to your Muffin_ application.

Extract messages
----------------

Extract strings from your application to locales: ::

    $ muffin app_package babel_extract_messages [OPTIONS] appdir


Translate ``.po`` files and compile translations: ::

    $ muffin app_package babel_compile_messages [OPTIONS]


.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/muffin-babel/issues

.. _contributing:

Contributing
============

Development of Muffin-Babel happens at: https://github.com/klen/muffin-babel


Contributors
=============

* klen_ (Kirill Klenov)

.. _license:

License
========

Licensed under a `MIT license`_.

.. _links:


.. _klen: https://github.com/klen
.. _Muffin: https://github.com/klen/muffin
.. _Muffin-Jinja2: https://github.com/klen/muffin-jinja2
.. _Babel: http://babel.edgewall.org/

.. _MIT license: http://opensource.org/licenses/MIT
