#!/usr/bin/env python

# FRAME Format
FRAME_CPK         = "CPK"
FRAME_ZERO        = "E5 56 D1 9D"
FRAME_COPYRIGHT   = "(c)CRI"
FRAME_TOC         = "TOC"
FRAME_ITOC        = "ITOC"
FRAME_ETOC        = "ETOC"
FRAME_CRILAYLA    = "CRILAYLA"
FRAME_CRI         = "CRI"
FRAME_GIM         = "GIM"
FRAME_1RAW        = "1raw"
FRAME_80000024    = "80 00 00 24"
FRAME_PNG         = "PNG"

FRAME_HEADER_MAP = [
    ('CPK'                                               , FRAME_CPK),
    ('\xE5\x56\xD1\x9D' + '\x00' * 12                    , FRAME_ZERO),
    ('\x00' * 10 + '(c)CRI'                              , FRAME_COPYRIGHT),
    ('TOC'                                               , FRAME_TOC),
    ('ITOC'                                              , FRAME_ITOC),
    ('ETOC'                                              , FRAME_ETOC),
    ('CRILAYLA'                                          , FRAME_CRILAYLA),
#   ('CRI'                                               , FRAME_CRI),
    ('MIG.00.1PSP\x00'                                   , FRAME_GIM),
    ('1raw'                                              , FRAME_1RAW),
    ('\x80\x00\x00\x24\x03\x12\x04\x02\x00\x00\x56\x22'  , FRAME_80000024),
    ('\x89PNG\x0D\x0A\x1A\x0A'                           , FRAME_PNG),
]

def identify(header, nofail=False):
    for k, v in FRAME_HEADER_MAP:
        if header.startswith(k):
            return v
    if not nofail:
        raise Exception('Unable to recognize frame for "%s"' % repr(header));

from StringIO import StringIO
from struct import unpack
from contextlib import closing

def parseCriHeader(header):
    for i in xrange(4):
        if header[i*4 + 3] == '\x00':
            marker = header[:i*4 + 3].strip()
            size = unpack('<L', header[(i+1)*4: (i+2)*4])
            return (marker, size[0])

def extract_criframe(header, f):
    marker, size = parseCriHeader(header)
    data = f.read(size)
    if marker.startswith("CRILAYLA"):
        return [data, f.read(0x100)]
    return [data]

def extract_gim(header, f):
    with closing(StringIO()) as out:
        reserved = f.read(0x04)
        assert reserved == '\x02\x00\x00\x00'
        out.write(reserved)
        sizedata = infile.read(0x04)
        size, = unpack('<L', sizedata)
        out.write(sizedata)
        data = f.read(size)
        out.write(data)
        return [out.getvalue()]

def extract_1raw(header, f):
    with closing(StringIO()) as out:
        while True:
            data = f.read(0x10)
            if identify(data, True):
                break
            out.write(data)
        f.seek(-0x10, 1)
        return [out.getvalue()]

def extract_80000024(header, f):
    with closing(StringIO()) as out:
        while True:
            tmp = infile.read(0x04)
            out.write(tmp)
            if tmp == '\x80\x01\x00\x0E':
                break;
        return [out.getvalue()]

def extract_png(header, f):
    with closing(StringIO()) as out:
        prvdata = ''
        while True:
            data = f.read(0x10)
            hexdata = data.encode('hex')
            out.write(data)
            if (prvdata + hexdata).find('49454e44ae426082') >= 0:
                break
            else:
                prvdata = hexdata
        return [out.getvalue()]

def extract_none(header, f):
    return ['']

FRAME_EXTRACTOR_MAP = {
    FRAME_CPK       : extract_criframe,
    FRAME_ZERO      : extract_none,
    FRAME_COPYRIGHT : extract_none,
    FRAME_TOC       : extract_criframe,
    FRAME_ITOC      : extract_criframe,
    FRAME_ETOC      : extract_criframe,
    FRAME_CRILAYLA  : extract_criframe,
    FRAME_CRI       : extract_criframe,
    FRAME_GIM       : extract_gim,
    FRAME_1RAW      : extract_1raw,
    FRAME_80000024  : extract_80000024,
    FRAME_PNG       : extract_png,
}

def extract(typename, header, f):
    func = FRAME_EXTRACTOR_MAP[typename]
    if not func:
        raise Exception('Extractor for %s undefined' % typename)
    return func(header, f)

class DataFrame:
    """A Frame Of Data"""

    def __init__(s, offset, typename, header, data):
        s.offset = offset
        s.typename = typename
        s.header = header
        s.data = data

PADDING_LINE = '\x00' * 0x10

def readframe(f):
    while True:
        offset = f.tell()
        header = f.read(0x10)
        typename = identify(header)
        data = extract(typename, header, f)
        yield DataFrame(offset, typename, header, data)

        if f.tell() % 0x10 > 0:
            f.read(0x10 - f.tell() % 0x10)
        while True:
            padding = f.read(0x10)
            if padding == '':
                return;
            if padding != PADDING_LINE:
                break;
        f.seek(-0x10, 1)

# @UTF Table Constants Definition (From utf_table)
# Suspect that "type 2" is signed
COLUMN_STORAGE_MASK       = 0xf0
COLUMN_STORAGE_PERROW     = 0x50
COLUMN_STORAGE_CONSTANT   = 0x30
COLUMN_STORAGE_ZERO       = 0x10
COLUMN_TYPE_MASK          = 0x0f
COLUMN_TYPE_DATA          = 0x0b
COLUMN_TYPE_STRING        = 0x0a
# COLUMN_TYPE_FLOAT2      = 0x09 ?
# COLUMN_TYPE_DOUBLE      = 0x09 ?
COLUMN_TYPE_FLOAT         = 0x08
# COLUMN_TYPE_8BYTE2      = 0x07 ?
COLUMN_TYPE_8BYTE         = 0x06
COLUMN_TYPE_4BYTE2        = 0x05
COLUMN_TYPE_4BYTE         = 0x04
COLUMN_TYPE_2BYTE2        = 0x03
COLUMN_TYPE_2BYTE         = 0x02
COLUMN_TYPE_1BYTE2        = 0x01
COLUMN_TYPE_1BYTE         = 0x00

from array import array

def chiper(data):
    """Chiper for @UTF Table"""

    c, m = (0x5f, 0x15)
    v = array('B', data)
    for i in xrange(len(v)):
        v[i] = v[i] ^ c & 0b11111111
        c = c * m & 0b11111111
    return v.tostring()

class Field:

    def __init__(s, utf, f):
        s.typeid, s.nameoffset = unpack('>BL', f.read(0x05))
        s.name = utf.getstring(f, s.nameoffset)
        s.storagetype = s.typeid & COLUMN_STORAGE_MASK
        s.fieldtype = s.typeid & COLUMN_TYPE_MASK
        if s.feature(COLUMN_STORAGE_CONSTANT):
            if s.feature([
                    COLUMN_TYPE_8BYTE,
                    COLUMN_TYPE_DATA,
                    ]):
                s.data = f.read(8)
            elif s.feature([
                    COLUMN_TYPE_STRING, COLUMN_TYPE_FLOAT, 
                    COLUMN_TYPE_4BYTE2, COLUMN_TYPE_4BYTE,
                    ]):
                s.data = f.read(4)
            elif s.feature([
                    COLUMN_TYPE_2BYTE2, COLUMN_TYPE_2BYTE,
                    ]):
                s.data = f.read(2)
            elif s.feature([
                    COLUMN_TYPE_1BYTE2, COLUMN_TYPE_1BYTE,
                    ]):
                s.data = f.read(1)

    def feature(s, typeid):
        if type(typeid) == list:
            return s.storagetype in typeid or s.fieldtype in typeid or s.typeid in typeid
        else:
            return s.storagetype == typeid or s.fieldtype == typeid or s.typeid == typeid


class UTF:
    """@UTF Table Structure"""

    def __init__(s, data):
        if data.startswith('\x1F\x9E\xF3\xF5'):
            # If the data is encrypted
            s.data = chiper(data)
        else:
            s.data = data

        with closing(StringIO(s.data)) as f:
            (
                    s.marker, 
                    s.table_size, 
            ) = unpack('>4sL', f.read(0x08))
            assert s.marker == '@UTF'
            s.table_content = f.read(s.table_size)
            assert len(s.table_content) == s.table_size

        with closing(StringIO(s.table_content)) as f:
            (
                    s.rows_offset, 
                    s.string_table_offset, 
                    s.data_offset, # always == s.table_size
                    s.table_name_string, 
                    s.columns, 
                    s.row_width, 
                    s.rows
            ) = unpack('>LLLLHHL', f.read(0x18))

            # Table Name

            s.name = s.getstring(f, s.table_name_string)

            # Schema

            s.schema = s.__readschema(f)

    def __readschema(s, f):
        schema = []
        while len(schema) < s.columns:
            schema.append(Field(s, f))
        return schema

    def getstring(s, f, string):
        original = f.tell()
        f.seek(s.string_table_offset + string, 0)
        data = ''
        while True:
            tmp = f.read(1)
            if tmp == '\x00':
                break
            data += tmp
        f.seek(original, 0)
        return data


if __name__ == '__main__':

    LINE_WIDTH = 52

    def write_line(strline):
        print >>stderr, strline * LINE_WIDTH

    import argparse
    from sys import stderr

    parser = argparse.ArgumentParser(description='unpack a cpk archive')
    parser.add_argument('input', help='Input CPK file')
    args = parser.parse_args()

    infile = open(args.input, 'rb')

    print >>stderr, "Read %s..." % args.input

    STAT = {}

    for h, k in FRAME_HEADER_MAP:
        STAT[k] = 0

    frames = 0

    for frame in readframe(infile):
        if frame.typename in [FRAME_ZERO, FRAME_COPYRIGHT]: 
            # With no Data
            pass
        elif frame.typename in [FRAME_CPK, FRAME_TOC, FRAME_ITOC, FRAME_ETOC]:
            # @UTF Table Format
            table = UTF(frame.data[0])

            # print schema

            write_line('=')
            print "Schema %s (%s)" % (table.name, frame.typename)
            write_line('-')
            for field in table.schema:
                print "\t%02x %s" % (field.typeid, field.name)
                if field.feature(COLUMN_STORAGE_CONSTANT):
                    print "\t\t%s" % (field.data.encode('hex'))

            pass
        elif frame.typename in [FRAME_CRILAYLA]:
            # CRI Package
            pass
        else:
            # Raw File Frame
            pass

        # Statistic Information
        STAT[frame.typename] += 1
        frames += 1
        print >>stderr, "0x%010X Found Frame %-16s (0x%06X)\r" % \
                (frame.offset, frame.typename, len(frame.data[0])),

    write_line('=')
    print >>stderr, "Scanner Found %d Frames" % frames

    for h, k in FRAME_HEADER_MAP:
        print >>stderr, "%16s : %d" % (k, STAT[k])

    infile.close();

    exit(0);

