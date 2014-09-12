
# Internal Format
FRAGMENT_CPK         = "CPK"
FRAGMENT_TOC         = "TOC"
FRAGMENT_ITOC        = "ITOC"
FRAGMENT_ETOC        = "ETOC"
FRAGMENT_CRILAYLA    = "CRILAYLA"
FRAGMENT_RAW         = "RAW"

class Fragment:

    def __init__(s):
        s.offset = 0
        s.length = 0
        s.data = ''
        # dump to align
        s.align = 0x0800

    @classmethod
    def parse(cls, f, offset, length):
        s = cls()

        f.seek(offset)
        s.data = f.read(length)

        s.offset = offset
        s.length = length

        return s

    def dump(s, f):
        s.offset = f.tell()
        s.length = len(s.data)

        f.write(s.data)

        if f.tell() % s.align > 0:
            f.write('\x00' * (s.align - f.tell() % s.align))

