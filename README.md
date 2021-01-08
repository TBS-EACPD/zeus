# `zeus` 


## This isn't ready yet!

## What is this?

This is a collection of tools extracted from a multi-project django monolith. Because we're new to publishing packages, there are a few gotchas:

- This is a monolithic package/install. Consumers can't just install a part, but must install the entire thing. 
  - This also means the whole thing is versioned together. If we add a shiny new feature after a totally independent breaking change, consumers can't get the new feature without the breaking change.
- This tool doesn't include external dependencies, you will have to install those yourself. We did this so consumers don't need to install packages they may not use.

## List of packages and utilities

Utils are grouped by the following package names. That means you import them as so: 
```python
from zeus.vanilla import is_ascii
```

### `vanilla` 

- `is_ascii`
- `are_strings_close_enough`
- `group_by`


### `versioning` (coming soon)

Subclassing `versioning.core.VersionModel` will create a history model that is automatically updated on each save.

### `i18n`

Depends on django, bleach and mistune

- `TextMakerCreator(global_keys,text_file_paths)`
- `WatchingTextMakerCreator((global_keys,text_file_paths)`
  - if using `runserver` and `settings.DEBUG=True`, requires watchdog

### markdown

requires django, bleach and mistune to be installed

- `markdown`
- `is_md_valid`
- `sanitize_html`

## How to build dist and egginfo

```bash
# in this project:
python setup.py sdist
```

How to install this locally without pypi (test this right before deploying a new version)


```bash
# in other project
pip install mypackage --no-index --no-cache --find-links file:///abs_path/to/dir/dist


pip install zeus --no-index --no-cache --find-links file:///Users/acl/Documents/code/zeus/dist

```

**editable mode**

When refreshing a local package, you'll also need `pip uninstall -y zeus` in between installs. This is super annoying, fortunately there's an easier way for python to link directly to the sources so this isn't necessary:

```bash
pip install -e file:///absolute/path/to/zeus/

# or replace zeus in requirements.txt with the following (recommended)
# -e file:///absolute/path/to/zeus/

# to uninstall:
pip uninstall -y zeus
```



# Development

TODO: get postgres, CI, etc. configured in a similar fashion to titan

The development environment should similar to the OG titan

1. Install postgres postgres 9.6 and configure your `$PATH`
2. Set up the virtual environment 
3. run `createdb zeus-dev`