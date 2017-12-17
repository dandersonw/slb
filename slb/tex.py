import re

from process import (Doc, BulletRegion, ParagraphRegion)
from typing import Iterable, List, Tuple
from util import TextSource


class TexDoc(Doc):
    @staticmethod
    def get_region_types():
        return [ItemizeRegion, TexParagraphRegion]


class TexParagraphRegion(ParagraphRegion):
    def __init__(self, lines: Iterable[str]):
        super().__init__(lines)

    @staticmethod
    def _is_term_line_exclusive(line, state):
        return any(region_type.is_init_line(line, state)
                   for region_type in TexDoc.get_region_types()
                   if region_type != TexParagraphRegion)


class ItemizeRegion(BulletRegion):
    def __init__(self, lines):
        super().__init__(lines)

    START_RE = re.compile(r"\\begin{(enumerate|itemize)}")
    END_RE = re.compile(r"\\end{(enumerate|itemize)}")

    @staticmethod
    def _is_init_line_inclusive(line, state):
        return ItemizeRegion.START_RE.match(line) is not None

    @staticmethod
    def _is_term_line_inclusive(line, state):
        return ItemizeRegion.END_RE.match(line) is not None

    @classmethod
    def get_prefix(cls, src: TextSource) -> List[str]:
        return [next(src)]

    @staticmethod
    def split_bullet(line: str) -> Tuple[str, str]:
        m = re.match(r"(\\[a-z]+\[[^\]]+\] ?)(.+)", line)
        if m is not None:
            return m.groups()
        else:
            return None

    @staticmethod
    def following_line_indent(bullet) -> int:
        return 2

    @classmethod
    def get_suffix(cls, line: str) -> str:
        if cls.END_RE.match(line) is not None:
            return line
        else:
            return None

