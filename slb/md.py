import re

from process import Doc, TextRegion, ParagraphRegion, Paragraph, BulletRegion
from typing import Iterable, Tuple


class MdDoc(Doc):
    @staticmethod
    def get_region_types():
        return [MdCodeRegion, MdBlockQuoteRegion, MdBulletRegion, MdParagraphRegion]

    @staticmethod
    def _get_default_format_config():
        return {"can_flow": MdDoc.can_flow_paragraph}

    HEADER_RE = re.compile(r"^#")
    UNFLOWABLE_RE = [HEADER_RE]

    @staticmethod
    def can_flow_paragraph(paragraph: Paragraph):
        return not any(regex.search(paragraph.text) for regex in MdDoc.UNFLOWABLE_RE)


class MdCodeRegion(TextRegion):
    @staticmethod
    def _is_init_line_inclusive(line, state):
        return line.startswith("```")

    @staticmethod
    def _is_term_line_inclusive(line, state):
        return line.startswith("```")


class MdBlockQuoteRegion(TextRegion):
    def __init__(self, lines):
        super().__init__(lines)
        self.paragraph = Paragraph(l[3:] for l in self.lines)

    @staticmethod
    def _is_init_line_inclusive(line, state):
        return line.startswith(" > ")

    @staticmethod
    def _is_term_line_exclusive(line, state):
        return not line.startswith(" > ")

    def format_out(self, **kwargs):
        # TODO: adjust fill with by 3 characters?
        return [" > " + l for l in self.paragraph.format_out(**kwargs)]


class MdParagraphRegion(ParagraphRegion):
    def __init__(self, lines: Iterable[str]):
        super().__init__(lines)

    @staticmethod
    def _is_term_line_exclusive(line, state):
        return any(region_type.is_init_line(line, state)
                   for region_type in MdDoc.get_region_types()
                   if region_type != MdParagraphRegion)


class MdBulletRegion(BulletRegion):
    @staticmethod
    def _is_init_line_inclusive(line, state):
        return MdBulletRegion.split_bullet(line) is not None

    @staticmethod
    def _is_term_line_exclusive(line, state):
        return len(line.strip()) == 0

    @staticmethod
    def split_bullet(line: str) -> Tuple[str, str]:
        m = re.match(r"( *[-+*] ?)(.+)", line)
        if m is not None:
            return m.groups()
        else:
            return None
