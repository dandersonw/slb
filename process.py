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

    @staticmethod
    def is_init_line(line: str, state: Dict):
        return True

    @staticmethod
    def is_term_line(line: str, state: Dict):
        return False

    @classmethod
    def from_source(cls, source: TextSource, state: Dict):
        region_source = RegionSource(source, lambda l: cls.is_term_line(l, state))
        lines = list(region_source)
        return cls(lines)


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
        allocator = kwargs.get("allocator", nlp.Allocator)

        tokens = tokenizer.tokenize(self.text, **kwargs)
        token_lines = allocator.allocate(tokens)
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

