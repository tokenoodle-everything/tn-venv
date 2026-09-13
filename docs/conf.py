# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

project = "tn-venv"
copyright = "2026, tokenoodle-everything"
author = "tokenoodle-everything"

try:
    # Prefer the installed distribution metadata (single release source).
    release = version("tn-venv")
except PackageNotFoundError:
    # Docs built from a bare checkout: fall back to the package itself.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tn_venv.version import __version__ as release

version = ".".join(release.split(".")[:2])  # short X.Y.Z -> X.Y

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
