# Configuration file for the Garak API documentation built with Sphinx.

# Project information
project = 'Garak Security Scans API'
copyright = 'Garak Security Team'
author = 'Garak Security Team'
release = '1.0.0'

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinxcontrib.httpdomain',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output options
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# HTML theme options
html_theme_options = {
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

html_logo = None
html_favicon = None

# Custom sidebar
html_sidebars = {
    '**': [
        'relations.html',
        'searchbox.html',
    ]
}

# Extension configuration
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# HTTP domain configuration  
http_index_shortname = 'api'
http_index_localname = 'Garak Security Scans API'
http_strict_mode = False