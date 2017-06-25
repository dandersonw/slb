import re

from typing import Iterable


class Tokenizer:
    @classmethod
    def tokenize(cls, text: str, **kwargs) -> Iterable:
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


class Spacy(Tokenizer, Allocator):
    NLP = None

    @staticmethod
    def _get_nlp():
        import en_core_web_md
        if Spacy.NLP is None:
            Spacy.NLP = en_core_web_md.load()
        return Spacy.NLP

    @classmethod
    def tokenize(cls, text, **kwargs):
        return cls._get_nlp()(text)

    @staticmethod
    def join_tokens(tokens):
        if not tokens:
            return ""
        doc = tokens[0].doc
        print(tokens)
        return str(doc[tokens[0].i: (tokens[-1].i + 1)])

    @staticmethod
    def _total_token_lens(doc):
        lens = [0] * len(doc)
        commitment = 0
        for i in range(len(doc) - 1, -1, -1):
            if doc[i].whitespace_:
                commitment = 0
            t_len = len(doc[i])
            commitment += t_len
            lens[i] = commitment
        return lens

    @staticmethod
    def tag_desired_breaks(doc):
        doc_len = len(doc)
        break_at = [False] * doc_len
        for sent in doc.sents:
            if sent.end < doc_len:
                break_at[sent.end] = True

        for token in doc:
            if token.tag_ == "CC" and token.head.pos_ == "VERB":
                break_at[token.i] = True
        return break_at

    @classmethod
    def allocate(cls, doc, **kwargs):
        fill_width = kwargs.get("fill_width", 80)
        commitments = cls._total_token_lens(doc)
        break_at = cls.tag_desired_breaks(doc)
        lines = []
        line = []
        line_len = 0
        for token, commitment in zip(doc, commitments):
            token_len = len(token)
            if line_len + commitment > fill_width or break_at[token.i]:
                lines.append(line)
                line = []
                line.append(token)
                line_len = token_len + 1
            else:
                line_len += token_len
                line.append(token)
        if line:
            lines.append(line)
        return lines
