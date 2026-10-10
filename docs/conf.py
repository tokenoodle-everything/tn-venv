# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "tn-venv"
copyright = "2026, tokenoodle-everything"
author = "tokenoodle-everything"
release = "1.0.0"
version = "1.0.3"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

copybutton_prompt_text = r"> |\$ "
copybutton_prompt_is_regexp = True

myst_enable_extensions = [
    "strikethrough",
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
    "substitution",
]
myst_heading_anchors = 4

nitpicky = False

# Set a real-browser User-Agent so shields.io (and other image hosts
# that gate on UA) return 200 to Sphinx's image downloader. The
# default `Python-urllib/3.x` UA is blocked by shields.io (it
# returns 403, which MyST renders as a broken-image icon). This
# setting is harmless for any other remote image.
import urllib.request as _urllib_request

_orig_urlopen = _urllib_request.urlopen


def _patched_urlopen(url, *args, **kwargs):
    req_or_url = url
    if isinstance(url, str):
        req_or_url = _urllib_request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Sphinx; tn-venv-docs) "
                    "AppleWebKit/537.36 (KHTML, like Gecko)"
                ),
            },
        )
    return _orig_urlopen(req_or_url, *args, **kwargs)


_urllib_request.urlopen = _patched_urlopen

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
# CNAME is copied verbatim into the build output so GitHub Pages picks up
# the custom domain from the deployed artifact.
html_extra_path = ["CNAME"]
html_title = f"tn-venv {release}"
html_theme_options = {
    "navigation_depth": 4,
    "sticky_navigation": True,
    "style_external_links": True,
    "titles_only": False,
}
html_show_sourcelink = True
