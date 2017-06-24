#! /usr/bin/env python

import argparse
import process
import util
import md


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i",
                        help="Input path. Default or \"-\" is stdin.",
                        default="/dev/stdin")
    args = parser.parse_args()

    with open(args.i, mode="r", encoding="utf-8") as inputFile:
        source = util.FileTextSource(inputFile)
        doc = md.MdDoc.from_source(source)

    for region in doc.regions:
        print("-" * 60)
        if isinstance(region, process.ParagraphRegion):
            for p in region.paragraphs:
                print(p.text)
                print("-" * 20)
        else:
            print(type(region))


if __name__ == "__main__":
    main()
