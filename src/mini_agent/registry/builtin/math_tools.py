"""
registry/builtin/math_tools.py
---------------------------------
Math and small utility tools.
"""

import ast
import operator
import random
import uuid

from ..tools import Tool

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op_func = _ALLOWED_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError("Operator not allowed")
        return op_func(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_func = _ALLOWED_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError("Operator not allowed")
        return op_func(_safe_eval(node.operand))
    raise ValueError("Expression not allowed")


def calculator(expression: str) -> str:
    """Safely evaluates a math expression (e.g. '12 * (3 + 4)')."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


def generate_uuid() -> str:
    """Generates a new random UUID (useful for IDs, filenames, etc.)."""
    return str(uuid.uuid4())


def random_number(min_value: int = 0, max_value: int = 100) -> str:
    """Returns a random integer between min_value and max_value (inclusive)."""
    return str(random.randint(min_value, max_value))


def word_count(text: str) -> str:
    """Counts words in a piece of text."""
    return str(len(text.split()))


MATH_TOOLS = [
    Tool(name="calculator", description="Evaluates a math expression", func=calculator),
    Tool(name="generate_uuid", description="Generates a random UUID", func=generate_uuid),
    Tool(name="random_number", description="Generates a random integer in a range", func=random_number),
    Tool(name="word_count", description="Counts words in a text", func=word_count),
]
