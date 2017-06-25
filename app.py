#! /usr/bin/env python

import argparse
import process
import util
import md
import nlp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i",
                        help="Input path. Default or \"-\" is stdin.",
                        default="/dev/stdin")
    args = parser.parse_args()

    with open(args.i, mode="r", encoding="utf-8") as inputFile:
        source = util.FileTextSource(inputFile)
        doc = md.MdDoc.from_source(source)
        print("\n".join(doc.format_out(tokenizer=nlp.Spacy, allocator=nlp.Spacy)))


if __name__ == "__main__":
    main()
