from typing import Callable


class TextSource:
    def __iter__(self):
        return self

    def __next__(self):
        return NotImplementedError()

    def peek(self):
        return NotImplementedError()

    def has_next(self):
        try:
            self.peek()
        except StopIteration:
            return False
        return True


class FileTextSource(TextSource):
    def __init__(self, file):
        self.file = file
        self.head = None

    def __next__(self):
        if self.head is not None:
            temp = self.head
            self.head = None
            return temp
        n = next(self.file)
        print(n)
        return n

    def peek(self):
        if self.head is None:
            self.head = next(self.file)
        return self.head


class RegionSource(TextSource):
    def __init__(self, source: TextSource, stop_predicate: Callable[[str], bool]):
        self.source = source
        self.stop_predicate = stop_predicate

    def __next__(self):
        head = self.source.peek()
        if (self.stop_predicate(head)):
            raise StopIteration()
        else:
            return next(self.source)

    def peek(self):
        head = self.source.peek()
        if (self.stop_predicate(head)):
            raise StopIteration()
        else:
            return head

