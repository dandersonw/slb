#! /usr/bin/env python

import argparse
import sys
import os.path
sys.path.append(os.path.realpath("./slb"))
import process
import util
import md, tex
import nlp
import socket
import slbserver


def main():
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=print_help)
    parser.set_defaults(parser=parser)
    
    subparsers = parser.add_subparsers()

    common = argparse.ArgumentParser(add_help=False)
    common.set_defaults(infer_file_format=True)
    common.add_argument("-w",
                        help="Desired length of lines.",
                        type=int,
                        default=80)
    common.add_argument("-i",
                        help="Input path. Default or \"-\" is stdin.",
                        default="/dev/stdin")
    common.add_argument("-f",
                        help="Input file format")
    common.add_argument("-no-infer-format",
                         help="Don't infer the format of the input file",
                         dest="infer_file_format",
                         action="store_false")

    batch = subparsers.add_parser("batch", parents=[common])
    batch.set_defaults(func=batch_process)

    start = subparsers.add_parser("start", parents=[common])
    start.set_defaults(func=start_server)

    client = subparsers.add_parser("client", parents=[common])
    client.add_argument("--host",
                        help="Host to connect to",
                        default="localhost")
    client.add_argument("--port",
                        help="Port to connect to",
                        default=slbserver.PORT)
    client.set_defaults(func=client_process)

    args = parser.parse_args()
    args.func(args)


def print_help(args):
    args.parser.print_help()


def batch_process(args):
    format_kwargs = get_format_args(args)
    doc_class = resolve_doc_type(args)
    with open(args.i, mode="r", encoding="utf-8") as inputFile:
        source = util.FileTextSource(inputFile)
        doc = doc_class.from_source(source)
        print("\n".join(doc.format_out(**format_kwargs)))


def start_server(args):
    server = slbserver.SlbDaemon()
    server.run()


def resolve_doc_type(args) -> process.Doc:
    DEFAULT_FORMAT = "md"
    format_str = None
    if args.f is not None:
        format_str = args.f

    extension_to_format = {"md": "md",
                           "tex": "tex"}
        
    file_tail = args.i[-4:]
    if format_str is None and args.infer_file_format \
       and "." in file_tail:
        extension = file_tail.split(".")[1]
        if extension in extension_to_format:
            format_str = extension_to_format[extension]

    if format_str is None:
        format_str = DEFAULT_FORMAT

    format_to_class = {"md": md.MdDoc,
                       "tex": tex.TexDoc}
    return format_to_class[format_str]


def client_process(args):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((args.host, args.port))
        with open(args.i, mode="rb") as inputFile:
            file_bytes = inputFile.read()
        header = slbserver.make_request_header(len(file_bytes))
        sock.sendall(header)
        sock.sendall(file_bytes)
        response = slbserver.read_response(sock)
        print(response[1])


def get_format_args(args):
    return {"fill_width": args.w}


if __name__ == "__main__":
    main()
