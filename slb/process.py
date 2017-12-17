import re
import itertools
import nlp

from util import TextSource, RegionSource, FileTextSource
from typing import Iterable, Dict, List, Tuple


class TextRegion:
    def __init__(self, lines: Iterable[str]):
        self.lines = list(lines)

    def format_out(self, **kwargs) -> Iterable[str]:
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
        return self._separate_paragraphs(p.format_out(**kwargs) for p in self.paragraphs)

    @staticmethod
    def _separate_paragraphs(paragraphs: Iterable[Iterable[str]]):
        first_paragraph = True
        for paragraph in paragraphs:
            if first_paragraph:
                first_paragraph = False
            else:
                yield ""
            for line in paragraph:
                yield line


class BulletRegion(TextRegion):
    def __init__(self, lines: Iterable[str]):
        super().__init__(lines)

        src = FileTextSource(l for l in lines)
        self.prefix = self.get_prefix(src)
        self.suffix = []
        self.bullets = []
        bullets = []
        bullet = None
        blines = []

        while True:
            try:
                line = next(src)
                if bullet is None:
                    bullet, first_line = self.split_bullet(line)
                    blines = [first_line]
                elif self.is_continuation(line, bullet):
                    meat = self.split_continuation(line, bullet)
                    blines.append(meat)
                elif self.split_bullet(line) is not None:
                    doc = self.get_doc_class().\
                          from_source(FileTextSource(l for l in blines))
                    bullets.append((bullet, doc))
                    bullet, first_line = self.split_bullet(line)
                    blines = [first_line]
                elif self.get_suffix(line) is not None:
                    self.suffix = [line]
                else:
                    print(line)
                    raise ValueError()
            except StopIteration:
                break

        if bullet is not None:
            doc = self.get_doc_class().\
                  from_source(FileTextSource(l for l in blines))
            bullets.append((bullet, doc))
        self.bullets = bullets
    
    @classmethod
    def is_continuation(cls, line: str, bullet: str) -> bool:
        indent = " " * cls.following_line_indent(bullet)
        return line.startswith(indent)

    @classmethod
    def split_continuation(cls, line: str, bullet: str) -> str:
        return line[cls.following_line_indent(bullet):]
    
    @classmethod
    def get_prefix(cls, src: TextSource) -> List[str]:
        return []

    @classmethod
    def get_suffix(cls, line: str) -> str:
        return None

    @staticmethod
    def get_doc_class():
        return Doc

    @staticmethod
    def following_line_indent(bullet) -> int:
        return len(bullet)

    @staticmethod
    def split_bullet(line: str) -> Tuple[str, str]:
        m = re.match(r"( *[-+*] ?)(.+)", line)
        if m is not None:
            return m.groups()
        else:
            return None

    def format_out(self, **kwargs):
        fill_width = kwargs.get("fill_width", 80)

        for l in self.prefix:
            yield l
        for bullet, doc in self.bullets:
            indent = self.following_line_indent(bullet)
            new_kwargs = kwargs.copy()
            new_kwargs["fill_width"] = fill_width - indent
            for line in doc.format_out(**kwargs):
                if bullet is not None:
                    yield bullet + line
                    bullet = None
                elif len(line.strip()) == 0:
                    continue
                else:
                    yield " " * indent + line
        for l in self.suffix:
            yield l


class Doc:
    def __init__(self, regions: Iterable[TextRegion]):
        self.regions = list(regions)

    def format_out(self, **kwargs) -> Iterable[str]:
        default_config = self._get_default_format_config()
        for key in default_config:
            if key not in kwargs:
                kwargs[key] = default_config[key]
        return self._separate_regions(r.format_out(**kwargs) for r in self.regions)

    @staticmethod
    def _get_default_format_config():
        return dict()

    @staticmethod
    def _separate_regions(regions: Iterable[Iterable[str]]):
        first_region = True
        for region in regions:
            if first_region:
                first_region = False
            else:
                yield ""
            for line in region:
                yield line

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
            return self.lines

        tokenizer = kwargs.get("tokenizer", nlp.Tokenizer)
        wlen_f = kwargs.get("token_wlen_f", tokenizer.token_len_with_whitespace)
        allocator = kwargs.get("allocator", nlp.Allocator)

        tokens = tokenizer.tokenize(self.text, **kwargs)
        token_lines = allocator.allocate(tokens, wlen_f, **kwargs)
        return [tokenizer.join_tokens(token_line) for token_line in token_lines]

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

