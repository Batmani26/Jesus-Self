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


# Match expressions like: 5+3, 12 * 4, (7-2)/5, 10/2
_EXPR_RE = re.compile(r"^[\d\s+\-*/().]+$")
_HAS_OP = re.compile(r"[+\-*/]")


def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True))
    async def auto_calc(event: events.NewMessage.Event) -> None:
        # cheap early exits first (avoid heavy work on every message)
        txt = (event.raw_text or "").strip()
        if not txt or len(txt) > 60 or txt.startswith(p):
            return
        if not _HAS_OP.search(txt) or not _EXPR_RE.match(txt):
            return
        try:
            from bot.main import CALC_ENABLED
        except Exception:
            CALC_ENABLED = {"on": True}
        if not CALC_ENABLED.get("on", True):
            return
        # must contain at least one digit and one operator
        if not re.search(r"\d", txt):
            return
        try:
            result = safe_eval(txt)
            # format nicely
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            await event.reply(f"🧮 **{txt} = {result}**")
        except Exception:
            pass
