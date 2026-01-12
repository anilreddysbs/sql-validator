import importlib
import pkgutil
import json

RULES_PACKAGE = "validator.rules"

class RuleEngine:
    def __init__(self, checks_config_path="config/checks.json"):
        # load config
        with open(checks_config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.rules = {}         # id → rule class object
        self.active_rules = []  # instantiated objects

        self._discover_rules()
        self._load_active_rules()

    def _discover_rules(self):
        """Dynamically discover all rules under validator.rules.*"""
        import validator.rules as rules_pkg
        pkgpath = rules_pkg.__path__

        for _, name, _ in pkgutil.iter_modules(pkgpath):
            modname = f"{RULES_PACKAGE}.{name}"
            mod = importlib.import_module(modname)

            from validator.rules.rule_base import RuleBase

            # find classes inheriting RuleBase
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, RuleBase)
                    and obj is not RuleBase
                ):
                    rid = getattr(obj, "id", None)
                    if rid:
                        self.rules[rid] = obj

    def _load_active_rules(self):
        """
        Instantiate rules that are enabled in config.
        Inject 'rule_name' into each instance automatically.
        """

        for rid, params in self.config.items():

            # Skip disabled rules
            if not params.get("enabled", False):
                continue

            rule_cls = self.rules.get(rid)

            if rule_cls is None:
                print(f"[RuleEngine] Warning: Rule '{rid}' not found in code. Skipping.")
                continue

            # Extract rule name from config
            rule_name = params.get("rule_name", rule_cls.__name__)

            # Inject name into params for access inside rule
            params = dict(params)  # copy
            params["rule_name"] = rule_name

            # Instantiate rule with params
            inst = rule_cls(params)

            # Attach convenience attribute
            inst.rule_name = rule_name

            self.active_rules.append(inst)

    def get_active_rules(self):
        return self.active_rules
