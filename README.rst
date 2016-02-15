Muffin-Babel
############

.. _description:

Muffin-Babel -- an extension to Muffin_ that adds localization support with help of babel_.

.. _badges:

.. image:: http://img.shields.io/travis/klen/muffin-babel.svg?style=flat-square
    :target: http://travis-ci.org/klen/muffin-babel
    :alt: Build Status

.. image:: http://img.shields.io/pypi/v/muffin-babel.svg?style=flat-square
    :target: https://pypi.python.org/pypi/muffin-babel

.. image:: http://img.shields.io/pypi/dm/muffin-babel.svg?style=flat-square
    :target: https://pypi.python.org/pypi/muffin-babel

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.3

.. _installation:

Installation
=============

**Muffin-Babel** should be installed using pip: ::

    pip install muffin-babel

.. _usage:

Usage
=====

Add **muffin_babel** to **PLUGINS** in your Muffin_ application config: ::

    import muffin

    app = muffin.Application(
        'example',

        PLUGINS=(
            'muffin_jinja2',
            'muffin_babel',
        )
    
    )

Setup a locale selector function: ::

    @app.ps.babel.locale_selector
    def set_locale(request):
        """ Return locale from GET lang-param or automatically. """
        return request.GET.get(
            'lang',

            # Get locale based on user settings
            app.ps.babel.select_locale_by_request(request)
        )

Use `app.ps.babel.gettext`, `app.ps.babel.pgettext`, `app.ps.babel.lazy_gettext` function in your
code: ::

    @app.register('/')
    def index(request):
        return app.ps.babel.gettext('Hello!')


Jinja2
------

The `Muffin-Babel` has integration with `Muffin-Jinja2`, so if you have
`muffin_jinja2` plugin enabled, the plugin provides `gettext` and `ngettext`
function in Jinja2 templates' context.

.. note:: `muffin_jinja2` should be enabled before `muffin_babel` in your application configuration.


Options
-------

========================== ==============================================================
 *BABEL_CONFIGURE_JINJA2*   Install i18n support to Muffin-Jinja2_  (``True``)
 *BABEL_DEFAULT_LOCALE*     Set default locale (``en``)
 *BABEL_DOMAIN*             Set default domain (``messages``)
 *BABEL_LOCALES_DIRS*       List of directories where locales are leaving
 *BABEL_SOURCES_MAP*        Babel sources map
 *BABEL_OPTIONS_MAP*        Babel options map
========================== ==============================================================

Commands
========

The plugin adds two commands to your Muffin_ application.

Extract messages
----------------

Extract strings from your application to locales: ::

    $ muffin app_module extract_messages [OPTIONS] appdir 


Translate ``.po`` files and compile translations: ::
    
    $ muffin app_module compile_messages [OPTIONS]


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
=======

Licensed under a `MIT license`_.

If you wish to express your appreciation for the project, you are welcome to send
a postcard to: ::

    Kirill Klenov
    pos. Severny 8-3
    MO, Istra, 143500
    Russia

.. _links:


.. _klen: https://github.com/klen
.. _Muffin: https://github.com/klen/muffin
.. _Muffin-Jinja2: https://github.com/klen/muffin-jinja2
.. _babel: http://babel.edgewall.org/

.. _MIT license: http://opensource.org/licenses/MIT
