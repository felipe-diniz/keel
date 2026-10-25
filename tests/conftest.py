import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "keel"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(filename):
    """Import a plugin script whose file name has a hyphen."""
    path = SCRIPTS / filename
    name = filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
