import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "openlock"))
add_module_names = False

project = "openlock"
copyright = "2024, Michel Van den Bergh"
author = "Michel Van den Bergh"
release = "1.2.1"

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = []

html_baseurl = "https://www.cantate.be/openlock"
html_permalinks_icon = "§"
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
