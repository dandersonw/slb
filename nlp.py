import re

from typing import Iterable


class Tokenizer:
    @staticmethod
    def tokenize(text: str, **kwargs) -> Iterable:
        return re.split(r"\s+", text)

    @staticmethod
    def join_tokens(tokens: Iterable) -> str:
        return " ".join(tokens)


class Allocator:
    @staticmethod
    def allocate(tokens: Iterable, **kwargs) -> Iterable[Iterable]:
        fill_width = kwargs.get("fill_width", 80)
        lines = []
        line = []
        line_len = 0
        for token in tokens:
            token_len = len(token)
            if line_len + token_len < fill_width:
                line_len += token_len
                line.append(token)
            else:
                lines.append(line)
                line = []
                line.append(token)
                line_len = token_len + 1
        if line:
            lines.append(line)
        return lines
