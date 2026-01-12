from typing import Dict

class RuleBase:
    """
    Base class for rules. Each rule may return:
      - "❌ ..." failure messages
      - "⚠️ ..." warning messages
      - "✅ ..." success messages
    """
    id = "base"
    rule_name = "Generic Rule"

    def __init__(self, params: Dict = None):
        self.params = params or {}

    def ok(self, msg: str) -> str:
        return f"✅ {msg}"

    def warn(self, msg: str) -> str:
        return f"⚠️ {msg}"

    def fail(self, msg: str) -> str:
        return f"❌ {msg}"

    def apply(self, statements, idx, context):
        raise NotImplementedError
