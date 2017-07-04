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
    def is_init_line(line, state):
        is_init = line.startswith("```")
        if is_init:
            state["md_code_just_init"] = True
        state["md_code_end_next"] = False
        return is_init

    @staticmethod
    def is_term_line(line, state):
        if state["md_code_just_init"]:
            state["md_code_just_init"] = False
            return False
        elif state["md_code_end_next"]:
            return True
        is_end = line.startswith("```")
        state["md_code_end_next"] = is_end
        return False


class MdParagraphRegion(ParagraphRegion):
    def __init__(self, lines: Iterable[str]):
        super().__init__(lines)

    @staticmethod
    def is_term_line(line, state):
        return any(region_type.is_init_line(line, state)
                   for region_type in MdDoc.get_region_types()
                   if region_type != MdParagraphRegion)
