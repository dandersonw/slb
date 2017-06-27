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
        return str(doc[tokens[0].i: (tokens[-1].i + 1)])

    @staticmethod
    def _total_token_lens(doc, illegal_at):
        lens = [0] * len(doc)
        commitment = 0
        for i in range(len(doc) - 1, -1, -1):
            t_len = len(doc[i])
            commitment += t_len
            lens[i] = commitment
            if not illegal_at[i]:
                commitment = 0
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

        for sent in doc.sents:
            has_break = any(break_at[i] for i in range(sent.start, sent.end))
            if len(sent) > 8 and not has_break:
                for t in sent:
                    if len(list(t.subtree)) > 4 and len(list(t.head.children)) == 2:
                        break_at[t.i] = True

        for token in doc:
            if token.pos_ == "PUNCT":
                break_at[token.i] = False
        return break_at

    @staticmethod
    def tag_illegal_breaks(doc):
        illegal = [False] * len(doc)
        for token in doc[:-1]:
            if not token.whitespace_:
                illegal[token.i + 1] = True
        return illegal

    @classmethod
    def allocate(cls, doc, **kwargs):
        fill_width = kwargs.get("fill_width", 80)
        break_at = cls.tag_desired_breaks(doc)
        illegal_at = cls.tag_illegal_breaks(doc)
        commitments = cls._total_token_lens(doc, illegal_at)
        lines = []
        line = []
        line_len = 0
        i = 0
        while i < len(doc):
            token = doc[i]
            commitment = commitments[i]
            token_len = len(token.text_with_ws)
            if (line_len + commitment > fill_width or break_at[token.i]) and not illegal_at[i]:
                lines.append(line)
                line = []
                line_len = 0
                append_token = True
                while i < len(doc) and append_token:
                    line.append(doc[i])
                    line_len += len(doc[i].text_with_ws)
                    append_token = illegal_at[i + 1] if i < len(doc) - 1 else False
                    i += 1
            else:
                line_len += token_len
                line.append(token)
                i += 1

        if line:
            lines.append(line)
        return lines
