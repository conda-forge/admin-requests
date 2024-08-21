import importlib
import pkgutil
from . import archive_feedstock, mark_broken, token_reset, access_control, cfep3_copy

actions = {}

def get_actions():
    return actions.copy()


def register_action(name, module):
    assert name not in actions
    actions[name] = module


def register_actions():
    register_action("archive", archive_feedstock)
    register_action("unarchive", archive_feedstock)
    register_action("broken", mark_broken)
    register_action("not_broken", mark_broken)
    register_action("token_reset", token_reset)
    register_action("travis", access_control)
    register_action("cirun", access_control)
    register_action("cfep3_copy", cfep3_copy)
    for pkg in pkgutil.iter_modules():
        if pkg.name.startswith("conda_forge_admin_requests_"):
            spec = importlib.util.find_spec(pkg.name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            getattr(module, "register_actions")()

