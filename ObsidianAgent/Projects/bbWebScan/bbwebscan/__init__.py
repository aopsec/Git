from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("bbwebscan")
except PackageNotFoundError:  # editable install before `pip install -e .`
    __version__ = "0.0.0+local"
