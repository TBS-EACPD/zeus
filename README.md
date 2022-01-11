# `zeus` 


## Docs are still lagging...

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


### `versioning`

versioning model behaviour has no external dependencies.

Subclassing `versioning.core.VersionModel` will create a history model that is automatically updated on each save. See the [example](./django_sample/models.py) 

### `changelog` (in progress)

changelogs requires many external dependencies: graphene, aiodataloader, graphene-django

creating changelogs currently require a lot of boilerplate code. 

TODO: create a function that abstracts away all the graphql and allows querying paginated changelog data for specific models, fields, users and dates. 


### `i18n`

Depends on django, bleach, mistune and pyyaml

- `TextMakerCreator(global_keys,text_file_paths)`
- `WatchingTextMakerCreator((global_keys,text_file_paths)`
  - if using `runserver` and `settings.DEBUG=True`, requires watchdog

### `markdown`

requires django, bleach and mistune to be installed

- `markdown`
- `is_md_valid`
- `sanitize_html`

## Installing


```bash
pip install titan-zeus
```

### Installing from git with branch 

the entry in `requirements.txt` should look like this 

```ini
git+git://github.com/TBS-EACPD/zeus@release-0.1#egg=zeus
```

If you installed using git and want to update, you'll need to run `pip uninstall -y zeus` before re-running `pip install`  

## Building 

### How to build dist and egginfo

```bash
# in this project:
python setup.py sdist
```

How to install this locally without pypi (test this right before deploying a new version)


### editable mode

When refreshing a local package, you'll also need `pip uninstall -y zeus` in between installs. This is super annoying, fortunately there's an easier way for python to link directly to the sources so this isn't necessary:

```bash
pip uninstall zeus

# then replace zeus in requirements.txt with the following
# -e file:///absolute/path/to/zeus/

```

### locally packaged mode

Once you've got something that work in editable mode, try packaging the app

```bash
# in zeus project
python setup.py sdist

# in consumer project
pip uninstall -y zeus
# replace the zeus entry in requirements.txt with 
#file:///absolute/path/to/zeus/
```



# Development

1. Install postgres and configure your `$PATH`
2. Set up the virtual environment 
3. we run tests against a postgres DB, so you'll need to run `createdb zeus-dev`
