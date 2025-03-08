import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

project = 'Manticore OrderBook'
copyright = '2025, Manticore Technologies'
author = 'Manticore Technologies'
release = '1.0.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}
