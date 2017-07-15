
import socketserver
import process
import nlp
import struct
import md

PORT = 29010
REQUEST_HEADER_FMT = "L"
RESPONSE_HEADER_FMT = "L"


class SlbDaemon():
    def run(self):
        with socketserver.TCPServer(("localhost", PORT), SlbRequestHandler) as server:
            server.serve_forever()


class SlbRequestHandler(socketserver.BaseRequestHandler):
    @staticmethod
    def _make_response_header(size):
        return struct.pack(RESPONSE_HEADER_FMT, size)

    def handle(self):
        self.request.settimeout(1)
        data = SocketSource(self.request)
        doc = md.MdDoc.from_source(data)
        response_bytes = bytes("\n".join(doc.format_out()), "utf-8")
        header = self._make_response_header(len(response_bytes))
        self.request.sendall(header)
        self.request.sendall(response_bytes)


def make_request_header(size):
    return struct.pack(REQUEST_HEADER_FMT, size)


def read_response_header(sock):
    header = struct.unpack(RESPONSE_HEADER_FMT,
                           sock.recv(struct.calcsize(RESPONSE_HEADER_FMT))) 
    return {"size": header[0]}


def read_response(sock):
    header = read_response_header(sock)
    return (header, _read_utf8(sock, header["size"]))


def _read_utf8(sock, size):
    bytes_read = 0
    read = bytearray(b'\0' * size)
    while bytes_read < size:
        f = bytes_read
        t = min(bytes_read + 4096, size)
        bytes_read += sock.recv_into(memoryview(read)[f: t])
    return str(read, "utf-8")


class SocketSource(process.TextSource):
    def __init__(self, sock):
        self.sock = sock
        self.chars_returned = 0
        self.head = None
        self._read()

    def _read(self):
        header = struct.unpack(REQUEST_HEADER_FMT,
                               self.sock.recv(struct.calcsize(REQUEST_HEADER_FMT)))
        bytesize = header[0]
        self.buffer = _read_utf8(self.sock, bytesize)

    def __next__(self):
        if self.head is not None:
            temp = self.head
            self.head = None
            return temp

        if self.chars_returned >= len(self.buffer):
            raise StopIteration()

        idx = self.buffer.find("\n", self.chars_returned)
        idx = idx + 1 if idx != -1 else len(self.buffer)
        to_return = self.buffer[self.chars_returned: idx]
        self.chars_returned = idx
        print("\"" + to_return.rstrip() + "\"")
        return to_return.rstrip()

    def peek(self):
        if self.head is None:
            self.head = next(self)
        return self.head
