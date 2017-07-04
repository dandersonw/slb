import re

from process import Doc, TextRegion, ParagraphRegion, Paragraph
from typing import Iterable


class MdDoc(Doc):
    @staticmethod
    def get_region_types():
        return [MdCodeRegion, MdParagraphRegion]

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


class MdParagraphRegion(ParagraphRegion):
    def __init__(self, lines: Iterable[str]):
        super().__init__(lines)

    @staticmethod
    def _is_term_line_exclusive(line, state):
        return any(region_type.is_init_line(line, state)
                   for region_type in MdDoc.get_region_types()
                   if region_type != MdParagraphRegion)
