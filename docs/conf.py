# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "tn-venv"
copyright = "2026, tokenoodle-everything"
author = "tokenoodle-everything"
release = "0.1.0"
version = "0.1.2"

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
