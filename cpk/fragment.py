from struct import pack, unpack

# Internal Format
FRAGMENT_CPK         = "CPK"
FRAGMENT_TOC         = "TOC"
FRAGMENT_ITOC        = "ITOC"
FRAGMENT_ETOC        = "ETOC"

FRAGMENT_HEADERS = [ FRAGMENT_CPK, FRAGMENT_TOC, FRAGMENT_ITOC, FRAGMENT_ETOC ]

def detect_fragment_type(header):
    for k in FRAGMENT_HEADERS:
        if header.startswith(k):
            return k

def parse_cri_header(header):
    for i in xrange(4):
        if header[i*4 + 3] == '\x00':
            marker = header[:i*4 + 3].strip()
            size = unpack('<L', header[(i+1)*4: (i+2)*4])
            return (marker, size[0])

def make_cri_header(cri, length):
    s = ''
    s += cri + '0x00' * (4 - len(cri) % 4)
    s += pack('<L', length)
    s += '0x00' * (0x10 - len(s) % 0x10)
    return s

class Fragment:

    align = 0x0800

    def __init__(s):
        s.offset = 0
        s.length = 0
        s.data = ''
        # dump to align
        s.align = Fragment.align
        s.special = None

    @classmethod
    def parse(cls, f, offset, length):
        s = cls()

        f.seek(offset)
        s.data = f.read(length)

        s.offset = offset
        s.length = length

        f.seek((f.tell() / s.align + 1) * s.align)

        return s

    @classmethod
    def special(cls, f, offset):
        f.seek(offset)

        header = f.read(0x10)

        special = detect_fragment_type(header)
        _, size = parse_cri_header(header)

        s = Fragment.parse(f, offset, size + 0x10);
        s.data = s.data[0x10:]
        s.length -= 0x10
        s.special = special

        return s

    def dump(s, f):
        s.offset = f.tell()
        s.length = len(s.data)

        if s.special:
            f.write(make_cri_header(s.special, len(s.data)))

        f.write(s.data)

        if s.special == FRAGMENT_CPK:
            # special padding pattern for cpk fragment
            f.write('\x00' * (0x10 - f.tell() % 0x10))
            f.write('\xE5\x56\xD1\x9D' + '\x00' * 12)
            f.write('\x00' * (s.align - f.tell() % s.align))
            f.seek(-0x10, 1)
            f.write('\x00' * 10 + '(c)CRI')
        else:
            if f.tell() % s.align > 0:
                f.write('\x00' * (s.align - f.tell() % s.align))

