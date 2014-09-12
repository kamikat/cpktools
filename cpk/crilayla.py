from struct import pack, unpack
from bitarray import bitarray

class CompressedIO:

    def __init__(s, data):
        s.b = bitarray()
        s.b.frombytes(data[::-1])
        s.pos = 0

    def read(s, length):
        data = s.b[s.pos:s.pos+length]
        s.pos += length
        return data

    def read01(s, length):
        return s.read(length).to01()

    def readnum(s, length):
        return int(s.read01(length), 2)

    def readbyte(s, length = 1):
        return s.read(length * 8).tobytes()

    def tell(s):
        return s.pos

    def seek(s, offset, t = 0):
        if t == 0:
            s.pos = offset
        elif t == 1:
            s.pos += offset
        elif t == 2:
            s.pos = len(data) - 1 - offset

    def close(s):
        s.b = None

def deflate_levels():
    for v in [2, 3, 5, 8]:
        yield v
    while True:
        yield 8

from contextlib import nested

def deflate_crilayla(data, size, feed):
    MINIMAL_REFLEN = 3
    with nested(closing(CompressedIO(data)), closing(StringIO())) as (f, out):
        while True:
            feed(f.tell() >> 3, out.tell())
            bit = f.read01(1)
            if bit == '':
                break
            if int(bit, 2):

                offset = f.readnum(13) + MINIMAL_REFLEN
                refc = MINIMAL_REFLEN

                for lv in deflate_levels():
                    bits = f.read(lv)
                    refc += int(bits.to01(), 2)
                    if not bits.all():
                        break

                # DEBUG
                # curptr = out.tell()
                # refs = curptr - offset
                # s = out.getvalue()[refs: min(refs + refc, curptr)]
                # print >>stderr, 'Control 1 0x%08x(-0x%04x)=0x%08x 0x%04x (0x%04x)%s' % (curptr, offset, refs, refc, len(s), repr(s))

                assert out.tell() >= offset
                while refc > 0:
                    # read referenced bytes
                    out.seek(-offset, 1)
                    ref = out.read(refc)
                    out.seek(0, 2)
                    out.write(ref)
                    refc -= len(ref)

            else:
                # verbatim byte
                b = f.readbyte()

                # DEBUG
                # print >>stderr, 'Control 0 0x%08x %s' % (out.tell(), repr(b))

                out.write(b)

        return out.getvalue()[:size][::-1]

def uncompress(data, uncompressed_size, extract_size, file_size):

    header = data[:0x10]

    (
        marker, uncompressed_size, datasize
    ) = unpack('<8sLL', header)

    compressed_data = data[0x10: 0x10 + datasize]
    raw_data_header = data[0x10 + datasize: 0x10 + datasize + 0x100]

    assert marker == 'CRILAYLA'

    assert datasize + 0x0100 == file_size - 0x10
    #      ^ Compressed Data    ^ Frame Size^ Frame Header
    #                 ^ Uncompressed Header

    assert uncompressed_size + 0x0100 == extract_size
    #      ^ Uncompressed Data Size      ^ Original File Size
    #                          ^ Uncompressed Header

    # Uncompress
    data = deflate_crilayla(compressed_data, uncompressed_size)
    assert len(data) == uncompressed_size

    return raw_data_header + data


