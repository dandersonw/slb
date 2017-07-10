
import socketserver
import process
import nlp
import struct

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
        doc = process.Doc.from_source(data)
        response_bytes = bytes("\n".join(doc.format_out()),
                                   "utf-8")
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
    bytes_read = 0
    chunks = []
    while bytes_read < header["size"]:
        rcvd = sock.recv(4096)
        bytes_read += len(rcvd)
        chunks.append(str(rcvd, "utf-8"))
    return (header, "".join(chunks))


class SocketSource(process.TextSource):
    def __init__(self, sock):
        self.sock = sock
        self.buffer = ""
        self.bytes_read = 0
        self.head = None
        header = struct.unpack(REQUEST_HEADER_FMT,
                               sock.recv(struct.calcsize(REQUEST_HEADER_FMT)))
        self.size = header[0]

    def _read(self):
        while "\n" not in self.buffer and self.bytes_read < self.size:
            recvd = self.sock.recv(4096)
            self.bytes_read += len(recvd)
            self.buffer += str(recvd, "utf-8")
        if not self.buffer:
            raise StopIteration()

    def __next__(self):
        if self.head is not None:
            temp = self.head
            self.head = None
            return temp

        self._read()
        idx = self.buffer.find("\n")
        idx = idx if idx != -1 else len(self.buffer)
        to_return = self.buffer[:idx]
        self.buffer = self.buffer[idx + 1:]
        return to_return.rstrip()

    def peek(self):
        if self.head is None:
            self.head = next(self)
        return self.head
