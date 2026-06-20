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
sys.path.insert(0, os.path.abspath('../../../../src/testium/'))
sys.path.insert(0, os.path.abspath('../../../../src/'))


# -- Project information -----------------------------------------------------

project = "testium"
copyright = "2025, François Dausseur"
author = "François Dausseur"

# The full version, including alpha/beta/rc tags
try:
    release = os.environ["APP_VERSION"]
    version = release
except:
    raise Exception("APP_VERSION not defined in environment !")

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
master_doc = "index"
extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    'linuxdoc.rstFlatTable',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.

exclude_patterns = ["includes.rst", "templates.rst", "other_features.rst", "reports.rst"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = "alabaster"
html_theme = "classic"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

numfig = True

latex_engine = "xelatex"
# latex_logo only ships the file to the build dir; placement is done by the
# custom 'maketitle' element below (title + release, then logo, then the rest).
latex_logo = "testium_logo.pdf"
latex_elements = {
    "papersize": "a4paper",
    'fontpkg': r'''
    \setmainfont{DejaVu Sans}
    \setsansfont{DejaVu Sans}
    \setmonofont{DejaVu Sans Mono}
    ''',
    'preamble': r'''
    \usepackage{graphicx}
    \makeatletter
    % Keep Sphinx's title/page layout and add a small centered logo in the footer.
    \fancypagestyle{normal}{%
      \fancyhf{}%
      \fancyfoot[C]{\includegraphics[height=6mm]{testium_logo.pdf}}%
      \fancyfoot[RO]{{\py@HeaderFamily\thepage}}%
      \fancyfoot[LO]{{\py@HeaderFamily\nouppercase{\rightmark}}}%
      \fancyhead[RO]{{\py@HeaderFamily \@title\sphinxheadercomma\py@release}}%
      \if@twoside
        \fancyfoot[LE]{{\py@HeaderFamily\thepage}}%
        \fancyfoot[RE]{{\py@HeaderFamily\nouppercase{\leftmark}}}%
        \fancyhead[LE]{{\py@HeaderFamily \@title\sphinxheadercomma\py@release}}%
      \fi
      \renewcommand{\headrulewidth}{0.4pt}%
      \renewcommand{\footrulewidth}{0.4pt}%
    }
    % Chapter-opening / front-matter pages use 'plain': put the logo there too so
    % every page has it except the title page (its own empty style).
    \fancypagestyle{plain}{%
      \fancyhf{}%
      \fancyfoot[C]{\includegraphics[height=6mm]{testium_logo.pdf}}%
      \fancyfoot[RO]{{\py@HeaderFamily\thepage}}%
      \if@twoside\fancyfoot[LE]{{\py@HeaderFamily\thepage}}\fi
      \renewcommand{\headrulewidth}{0pt}%
      \renewcommand{\footrulewidth}{0.4pt}%
    }
    \makeatother
    ''',
    # Title page (replaces the \sphinxmaketitle call in the body): title +
    # release on top, then a large centered logo, then author / date.
    'maketitle': r'''
    \makeatletter
    \let\sphinxrestorepageanchorsetting\relax
    \ifHy@pageanchor\def\sphinxrestorepageanchorsetting{\Hy@pageanchortrue}\fi
    \hypersetup{pageanchor=false}%
    \begin{titlepage}%
      \let\footnotesize\small
      \let\footnoterule\relax
      \noindent\rule{\textwidth}{1pt}\par
      \begingroup
        \def\endgraf{ }\def\and{\& }%
        \pdfstringdefDisableCommands{\def\\{, }}%
        \hypersetup{pdfauthor={\@author}, pdftitle={\@title}}%
      \endgroup
      \begin{flushright}%
        \py@HeaderFamily
        {\Huge \@title \par}%
        {\itshape\LARGE \py@release\releaseinfo \par}%
      \end{flushright}%
      \vskip 2.5cm
      \begin{center}%
        \includegraphics[width=0.5\textwidth]{testium_logo.pdf}%
      \end{center}%
      \vfill
      \begin{flushright}%
        {\LARGE
          \begin{tabular}[t]{c}%
            \@author
          \end{tabular}\kern-\tabcolsep
          \par}%
        \vfill\vfill
        {\large
         \@date \par
         \vfill
         \py@authoraddress \par
        }%
      \end{flushright}%
      \@thanks
    \end{titlepage}%
    \setcounter{footnote}{0}%
    \let\thanks\relax\let\maketitle\relax
    \clearpage
    \ifdefined\sphinxbackoftitlepage\sphinxbackoftitlepage\fi
    \if@openright\cleardoublepage\else\clearpage\fi
    \sphinxrestorepageanchorsetting
    \makeatother
    '''
}
latex_show_urls = "footnote"

pdf_stylesheets = ["style_code_font_size"]

add_module_names = False # Remove namespaces from class/method signatures
