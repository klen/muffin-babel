# Muffin-Babel

[![Tests](https://github.com/klen/muffin-babel/workflows/tests/badge.svg)](https://github.com/klen/muffin-babel/actions)
[![PyPI Version](https://img.shields.io/pypi/v/muffin-babel)](https://pypi.org/project/muffin-babel/)
[![Python Versions](https://img.shields.io/pypi/pyversions/muffin-babel)](https://pypi.org/project/muffin-babel/)

**Muffin-Babel** is an extension for the [Muffin](https://github.com/klen/muffin) web framework that adds internationalization (i18n) support using [Babel](http://babel.edgewall.org/).

---

## Requirements

- Python >= 3.10

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
babel.setup(app, local_folders=["src/locale"])
```

### Inside a Route

```python
@app.route("/")
async def index(request):
    assert babel.current_locale
    return babel.gettext("Hello World!")
```

### Locale Selector

By default, locale is detected via the `Accept-Language` header. You can override it:

```python
@babel.locale_selector
async def get_locale(request):
    return request.query.get("lang") or await muffin_babel.select_locale_by_request(request, default="en")
```

### Direct Use

```python
@app.route("/")
def index(request):
    return babel.gettext("Hello!")
```

---

## Jinja2 Integration

If you're using the [`muffin-jinja2`](https://github.com/klen/muffin-jinja2) plugin, `Muffin-Babel` automatically injects `gettext` and `ngettext` functions into your Jinja2 templates.

---

## Plugin Options

| Option               | Default       | Description                               |
| -------------------- | ------------- | ----------------------------------------- |
| `AUTO_DETECT_LOCALE` | `True`        | Middleware for automatic locale detection |
| `CONFIGURE_JINJA2`   | `True`        | Enable i18n support in Jinja2 templates   |
| `DEFAULT_LOCALE`     | `"en"`        | Default fallback locale                   |
| `DOMAIN`             | `"messages"`  | Default domain name for translation files |
| `SOURCES_MAP`        | —             | File pattern to extractor method mapping  |
| `OPTIONS_MAP`        | —             | Options for extractor (e.g., encoding)    |
| `LOCAL_FOLDERS`      | `["locales"]` | Folders to search for translation files   |

Options can be passed directly during setup:

```python
babel.setup(app, default_locale="fr")
```

Or set via Muffin application config using the `BABEL_` prefix:

```python
BABEL_DEFAULT_LOCALE = "fr"
```

> Note: Muffin config keys are case-insensitive.

---

## Commands

The plugin adds commands to your Muffin app for message management.

### Extract Messages

Extract localizable strings from your app source:

```bash
$ muffin app_package babel_extract_messages [OPTIONS] appdir
```

### Compile Messages

Compile `.po` files into `.mo` binaries:

```bash
$ muffin app_package babel_compile_messages [OPTIONS]
```

---

## Export as CSV

You can also export your `.po` files to CSV:

```bash
$ muffin app_package babel_export_csv
```

This helps with sending strings to translators or spreadsheets.

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
