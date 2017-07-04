#! /usr/bin/env python

import argparse
import sys
import os.path
sys.path.append(os.path.realpath("./slb"))
import process
import util
import md
import nlp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i",
                        help="Input path. Default or \"-\" is stdin.",
                        default="/dev/stdin")
    parser.add_argument("-w",
                        help="Desired length of lines.",
                        type=int,
                        default=80)
    args = parser.parse_args()

    format_kwargs = get_format_args(args)

    with open(args.i, mode="r", encoding="utf-8") as inputFile:
        source = util.FileTextSource(inputFile)
        doc = md.MdDoc.from_source(source)
        print("\n".join(doc.format_out(tokenizer=nlp.Spacy,
                                       allocator=nlp.Spacy,
                                       **format_kwargs)))


def get_format_args(args):
    return {"fill_width": args.w}


if __name__ == "__main__":
    main()
