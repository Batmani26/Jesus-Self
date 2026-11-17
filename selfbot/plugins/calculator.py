"""Auto-calculator: if an outgoing message is a math expression with + - * /, reply with the answer."""
import re
import ast
import operator as op
from telethon import events

from selfbot.config import config

# Safe arithmetic evaluation (no eval)
_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod,
    ast.USub: op.neg, ast.UAdd: op.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("bad const")
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported")


def safe_eval(expr: str):
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


# Normalization: Persian/Arabic digits + unicode operators
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_OP_MAP = str.maketrans({"×": "*", "÷": "/", "٪": "%", "−": "-", "–": "-", "—": "-"})


def _normalize(text: str) -> str:
    t = text.translate(_FA_DIGITS).translate(_OP_MAP)
    t = t.replace(",", "")  # thousands separators
    return t.strip()


# Match expressions: digits, operators, parens, dot, spaces only
_EXPR_RE = re.compile(r"^[\d\s+\-*/().%]+$")
_HAS_OP = re.compile(r"[+\-*/%]")


def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True))
    async def auto_calc(event: events.NewMessage.Event) -> None:
        # cheap early exits first (avoid heavy work on every message)
        raw = (event.raw_text or "").strip()
        if not raw or len(raw) > 80 or raw.startswith(p):
            return
        txt = _normalize(raw)
        if not txt or len(txt) > 80:
            return
        if not _HAS_OP.search(txt) or not _EXPR_RE.match(txt):
            return
        if not re.search(r"\d", txt):
            return
        try:
            from bot.main import CALC_ENABLED
        except Exception:
            CALC_ENABLED = {"on": True}
        if not CALC_ENABLED.get("on", True):
            return
        try:
            result = safe_eval(txt)
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 6)
            await event.reply(f"🧮 **{txt} = {result}**")
        except Exception:
            pass
