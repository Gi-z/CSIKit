# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../../CSIKit'))

project = 'CSIKit'
copyright = '2021, Glenn Forbes'
author = 'Glenn Forbes'

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc"
]

templates_path = ['_templates']
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".venv"]

html_theme = 'alabaster'
html_static_path = ['_static']