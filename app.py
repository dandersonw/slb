#! /usr/bin/env python

import argparse
import sys
import os.path
sys.path.append(os.path.realpath("./slb"))
import process
import util
import md
import nlp
import socket
import slbserver


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-w",
                        help="Desired length of lines.",
                        type=int,
                        default=80)
    common.add_argument("-i",
                       help="Input path. Default or \"-\" is stdin.",
                       default="/dev/stdin")

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


def batch_process(args):
    format_kwargs = get_format_args(args)
    with open(args.i, mode="r", encoding="utf-8") as inputFile:
        source = util.FileTextSource(inputFile)
        doc = md.MdDoc.from_source(source)
        print("\n".join(doc.format_out(**format_kwargs)))


def start_server(args):
    server = slbserver.SlbDaemon()
    server.run()


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
