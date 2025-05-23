import re


def remove_backticks(text: str) -> str:
    return re.sub(r"```\w*\n(.*)\n```", r"\1", text, flags=re.DOTALL)
