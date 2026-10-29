# Muffin-Babel

[![Tests](https://github.com/klen/muffin-babel/workflows/tests/badge.svg)](https://github.com/klen/muffin-babel/actions)
[![PyPI Version](https://img.shields.io/pypi/v/muffin-babel)](https://pypi.org/project/muffin-babel/)
[![Python Versions](https://img.shields.io/pypi/pyversions/muffin-babel)](https://pypi.org/project/muffin-babel/)

**Muffin-Babel** is an extension for the [Muffin](https://github.com/klen/muffin) web framework that adds internationalization (i18n) support using [Babel](http://babel.edgewall.org/).

---

## Requirements

- Python >= 3.11

---

## Installation

Install via pip:

```bash
pip install muffin-babel
```

---

## Usage

### Basic Setup

```python
import muffin
import muffin_babel

app = muffin.Application("example")

# Initialize the plugin
babel = muffin_babel.Plugin()
babel.setup(app, locale_folders=["src/locale"])
```

### Inside a Route

```python
@app.route("/")
async def index(request):
    assert babel.current_locale
    return babel.gettext("Hello World!")
```

### Locale Selector

The locale is detected for every request by the plugin's selector. By default it uses the
`Accept-Language` header (`muffin_babel.select_locale_by_request`), but it can be replaced:

```python
@babel.locale_selector
async def get_locale(request):
    return request.query.get("lang") or await muffin_babel.select_locale_by_request(request)
```

The selector receives the request and returns a locale name (or `None` to fall back to the
`default_locale`). Detection is only active when `auto_detect_locale` is enabled.

### Current Locale

```python
babel.current_locale  # -> babel.Locale, default_locale until a request sets it
babel.current_locale = "ru"  # unknown locales are silently ignored

with babel.locale_ctx("ru"):
    babel.gettext("Hello World!")
```

---

## Translation Functions

| Function                                                              | Description                                          |
| --------------------------------------------------------------------- | ---------------------------------------------------- |
| `gettext(string, domain=None, **variables)`                           | Translate a string with the current locale           |
| `ngettext(singular, plural, num, domain=None, **variables)`           | Translate with plural forms, `num` chooses the form  |
| `pgettext(context, string, domain=None, **variables)`                 | Like `gettext` but with a context                    |
| `npgettext(context, singular, plural, num, domain=None, **variables)` | Like `ngettext` but with a context                   |
| `get_translations(domain=None, locale=None)`                          | Load the `babel.support.Translations` catalog itself |

```python
babel.gettext("Hello %(user)s", user="John")  # -> "Hello John"
babel.ngettext("%(num)s apple", "%(num)s apples", 2)  # -> "2 apples"
```

Variables are interpolated with the `%`-style mapping syntax. A missing variable is logged and
the untranslated string is returned. Catalogs are loaded on demand and cached per
`(domain, language)` for the process lifetime, so recompiled `.mo` files require a restart.

---

## Jinja2 Integration

With the [`muffin-jinja2`](https://github.com/klen/muffin-jinja2) plugin installed, `Muffin-Babel`
adds the `jinja2.ext.i18n` extension to the Jinja2 environment on startup and installs
`gettext` (with `%(name)s` interpolation) and `ngettext` as template globals. Both use the current
domain and locale:

```html
<h1>{{ gettext('Welcome!') }}</h1>
```

Set `configure_jinja2=False` (or `BABEL_CONFIGURE_JINJA2 = False` in the app config) to leave the
templates untouched.

---

## Plugin Options

| Option               | Default                                        | Description                               |
| -------------------- | ---------------------------------------------- | ----------------------------------------- |
| `auto_detect_locale` | `True`                                         | Middleware for automatic locale detection  |
| `configure_jinja2`   | `True`                                         | Enable i18n in the `muffin-jinja2` plugin  |
| `default_locale`     | `"en"`                                         | Default fallback locale                    |
| `domain`             | `"messages"`                                   | Default domain name for translation files  |
| `locale_folders`     | `["locales"]`                                  | Folders to search for translation files    |
| `sources_map`        | `[("**.py", "python"), ("**.html", "jinja2")]` | File pattern to extractor method mapping   |
| `options_map`        | `{"**.html": {"encoding": "utf-8"}}`           | Options for the extractors                 |

Options can be passed directly during setup:

```python
babel.setup(app, default_locale="fr")
```

Or set via Muffin application config using the `BABEL_` prefix:

```python
BABEL_DEFAULT_LOCALE = "fr"
```

> Note: Muffin config keys are case-insensitive. Unknown options are ignored silently, typos in
> option names are not reported.

---

## Commands

The plugin registers commands for the Muffin manage CLI.

### Extract Messages

Scan your sources and write (or update) a `.po` catalog in the first `locale_folders` entry —
`<locale_folders[0]>/<locale>/LC_MESSAGES/<domain>.po`:

```bash
$ muffin app_package babel-extract-messages [OPTIONS] [DIRNAMES ...]
```

- `DIRNAMES` — directories to scan (`sources_map` decides which extractor is used)
- `--project` — project name in the header (default: the application name)
- `--domain` — catalog domain (default: `messages`)
- `--no-locations` — do not write source line references
- `--charset` — output charset (default: `utf-8`)
- `--locale` — locale of the catalog to write (default: `default_locale`)

### Compile Messages

Compile every `<locale>/LC_MESSAGES/<domain>.po` of all `locale_folders` into `.mo` binaries:

```bash
$ muffin app_package babel-compile-messages [OPTIONS]
```

- `--use-fuzzy` — compile fuzzy entries as well
- `--domain` — catalog domain (default: `messages`)

### Export as CSV

Print a `.po` catalog as CSV (`id,string,context,comment`) to stdout:

```bash
$ muffin app_package babel-export-csv [OPTIONS]
```

- `--domain` — catalog domain (default: `messages`)
- `--locale` — locale to export (default: `default_locale`)

This helps with sending strings to translators or spreadsheets.

### Workflow

1. `babel-extract-messages` collects strings from the sources into a `.po` file.
2. Translators fill in the `.po` file (or work on the exported CSV).
3. `babel-compile-messages` produces the `.mo` files the application loads on demand.
4. Restart the application — the compiled catalogs are cached per process.

---

## Example

The [`example/`](example/) directory contains a runnable application with Russian translations:

```bash
uv run uvicorn example:app --port 5000
```

Then open <http://localhost:5000/?lang=ru>. The same command is available as `make example`.

---

## Contributing

Development happens at: [https://github.com/klen/muffin-babel](https://github.com/klen/muffin-babel)

Feel free to open issues or pull requests.

---

## Bug Tracker

Found a bug? Have a suggestion? Report it here:
👉 [https://github.com/klen/muffin-babel/issues](https://github.com/klen/muffin-babel/issues)

---

## License

Licensed under the [MIT license](http://opensource.org/licenses/MIT)

---

## Author

**[klen](https://github.com/klen)** (Kirill Klenov)
