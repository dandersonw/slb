import re
import itertools
import nlp

from util import TextSource, RegionSource
from typing import Iterable, Dict


class TextRegion:
    def __init__(self, lines: Iterable[str]):
        self.lines = list(lines)

    def format_out(self, **kwards) -> Iterable[str]:
        return self.lines

    @classmethod
    def is_init_line(cls, line: str, state: Dict):
        init = False
        if cls._is_init_line_inclusive(line, state):
            init = True
        if init:
            cls._set_state(state, "just_init", True)
        return init

    @staticmethod
    def _is_init_line_inclusive(line: str, state: Dict):
        return True

    @classmethod
    def is_term_line(cls, line: str, state: Dict):
        if cls._get_state(state, "just_init"):
            cls._set_state(state, "just_init", False)
            return False
        elif cls._get_state(state, "end_next"):
            cls._set_state(state, "end_next", False)
            return True
        if cls._is_term_line_exclusive(line, state):
            return True
        elif cls._is_term_line_inclusive(line, state):
            cls._set_state(state, "end_next", True)
            return False

    @staticmethod
    def _is_term_line_inclusive(line: str, state: Dict):
        return False

    @staticmethod
    def _is_term_line_exclusive(line: str, state: Dict):
        return False

    @classmethod
    def from_source(cls, source: TextSource, state: Dict):
        region_source = RegionSource(source, lambda l: cls.is_term_line(l, state))
        lines = list(region_source)
        return cls(lines)

    @classmethod
    def _get_state(cls, state, key):
        key = "{}_{}".format(cls.__name__, key)
        return state[key] if key in state else None

    @classmethod
    def _set_state(cls, state, key, val):
        key = "{}_{}".format(cls.__name__, key)
        state[key] = val


class ParagraphRegion(TextRegion):
    def __init__(self, lines: Iterable[str]):
        super().__init__(lines)
        self.paragraphs = list(Paragraph.from_lines(self.lines))

    def format_out(self, **kwargs):
        return itertools.chain.from_iterable(p.format_out(**kwargs) for p in self.paragraphs)


class Doc:
    def __init__(self, regions: Iterable[TextRegion]):
        self.regions = list(regions)

    def format_out(self, **kwargs) -> Iterable[str]:
        default_config = self._get_default_format_config()
        for key in default_config:
            if key not in kwargs:
                kwargs[key] = default_config[key]
        return itertools.chain.from_iterable(r.format_out(**kwargs) for r in self.regions)

    @staticmethod
    def _get_default_format_config():
        return dict()

    @staticmethod
    def get_region_types():
        return [ParagraphRegion]

    @classmethod
    def from_source(cls, source: TextSource):
        region_types = cls.get_region_types()
        regions = []
        state = dict()
        while source.has_next():
            head = source.peek()
            for region in region_types:
                if region.is_init_line(head, state):
                    regions.append(region.from_source(source, state))
                    break
        return cls(regions)


class Paragraph:
    def __init__(self, lines):
        self.lines = list(lines)
        self.text = self.join_read_lines(self.lines)

    def format_out(self, **kwargs):
        can_flow = kwargs.get("can_flow", lambda l: True)
        if not can_flow(self):
            return [""] + self.lines

        tokenizer = kwargs.get("tokenizer", nlp.Tokenizer)
        wlen_f = kwargs.get("token_wlen_f", tokenizer.token_len_with_whitespace)
        allocator = kwargs.get("allocator", nlp.Allocator)

        tokens = tokenizer.tokenize(self.text, **kwargs)
        token_lines = allocator.allocate(tokens, wlen_f, **kwargs)
        return [""] + [tokenizer.join_tokens(token_line) for token_line in token_lines]

    @staticmethod
    def join_read_lines(lines: Iterable) -> str:
        text = " ".join(lines)
        text = re.sub(r"\n", " ", text)
        text = re.sub(r"(\s)\s*", r"\1", text)
        return text

    @staticmethod
    def is_paragraph_breaker(line):
        return line == ""

    @classmethod
    def from_lines(cls, lines):
        current_paragraph = []
        for line in lines:
            if cls.is_paragraph_breaker(line):
                if current_paragraph:
                    yield cls(current_paragraph)
                current_paragraph = []
            else:
                current_paragraph.append(line)
        if current_paragraph:
            yield cls(current_paragraph)

