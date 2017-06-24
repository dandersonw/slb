import re
import itertools

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


class Doc:
    def __init__(self, regions: Iterable[TextRegion]):
        self.regions = list(regions)

    def format_out(self, **kwargs) -> Iterable[str]:
        return itertools.chain.from_iterable(r.format_out() for r in self.regions)

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

    @staticmethod
    def join_read_lines(lines: Iterable) -> str:
        text = "".join(lines)
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
                yield cls(current_paragraph)
                current_paragraph = []
            else:
                current_paragraph.append(line)
        if current_paragraph:
            yield cls(current_paragraph)

