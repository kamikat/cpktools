#!/usr/bin/env python

#######################
# Data Frame Fragment #
#######################

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

from cStringIO import StringIO
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
        s.utf = None

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

#######################
# @UTF Table Fragment #
#######################

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

COLUMN_TYPE_MAP = {
    COLUMN_TYPE_DATA    : '>LL',
    COLUMN_TYPE_STRING  : '>L',
    COLUMN_TYPE_FLOAT   : '>f',
    COLUMN_TYPE_8BYTE   : '>Q',
    COLUMN_TYPE_4BYTE2  : '>l',
    COLUMN_TYPE_4BYTE   : '>L',
    COLUMN_TYPE_2BYTE2  : '>h',
    COLUMN_TYPE_2BYTE   : '>H',
    COLUMN_TYPE_1BYTE2  : '>b',
    COLUMN_TYPE_1BYTE   : '>B',
}

class Field:

    def __init__(s, utf, f):
        s.typeid, s.nameoffset = unpack('>BL', f.read(0x05))
        s.name = utf.getstring(f, s.nameoffset)
        s.storagetype = s.typeid & COLUMN_STORAGE_MASK
        s.fieldtype = s.typeid & COLUMN_TYPE_MASK
        if s.feature(COLUMN_STORAGE_CONSTANT):
            pattern = COLUMN_TYPE_MAP[s.fieldtype]
            if not pattern:
                raise Exception("Unknown Type 0x%02x" % s.fieldtype)
            col_data = unpack(pattern, f.read(calcsize(pattern)))
            if s.feature(COLUMN_TYPE_STRING):
                col_data = (utf.getstring(f, col_data[0]), col_data[0])
            s.data = col_data

    def feature(s, typeid):
        if type(typeid) == list:
            return s.storagetype in typeid or s.fieldtype in typeid or s.typeid in typeid
        else:
            return s.storagetype == typeid or s.fieldtype == typeid or s.typeid == typeid

from struct import calcsize

def readrow(f, utf):
    for i in xrange(utf.row_length):
        start_offset = f.tell()
        row = []
        for s in utf.columns:
            if s.feature(COLUMN_STORAGE_CONSTANT):
                row.append(s.data)
            elif s.feature(COLUMN_STORAGE_ZERO):
                row.append(())
            elif s.feature(COLUMN_STORAGE_PERROW):
                pattern = COLUMN_TYPE_MAP[s.fieldtype]
                if not pattern:
                    raise Exception("Unknown Type 0x%02x" % s.fieldtype)
                col_data = unpack(pattern, f.read(calcsize(pattern)))
                if s.feature(COLUMN_TYPE_STRING):
                    col_data = (utf.getstring(f, col_data[0]), col_data[0])
                row.append(col_data)
        assert f.tell() - start_offset == utf.row_width
        yield row

class AttributeDict(dict): 
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

class UTF:
    """@UTF Table Structure"""

    def __init__(s, data):
        if data.startswith('\x1F\x9E\xF3\xF5'):
            # If the data is encrypted
            s.data = chiper(data)
            s.encrypted = True
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
                    s.column_length, 
                    s.row_width, 
                    s.row_length
            ) = unpack('>LLLLHHL', f.read(0x18))

            # Table Name

            s.name = s.getstring(f, s.table_name_string)

            # Schema

            s.columns = s.__readschema(f)

            # Rows Data

            assert f.tell() == s.rows_offset

            f.seek(s.rows_offset, 0)
            s.rows = s.__readrows(f)

            assert f.tell() == s.string_table_offset

    def __readschema(s, f):
        s.key2idx = {}
        s.schema = AttributeDict()
        schema = []
        while len(schema) < s.column_length:
            field = Field(s, f)
            s.key2idx[field.name] = len(schema)
            s.schema[field.name] = field
            schema.append(field)
        return schema

    def __readrows(s, f):
        rows = []
        for row in readrow(f, s):
            rows.append(row)
        return rows

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

    def value(s, key, row = 0):
        return s.rows[row][s.key2idx[key]]

#######################
# Uncompress Fragment #
#######################

class TableLibrary(dict):
    
    def __cpk(s, v):
        utf = v.utf

        assert utf.schema.ContentOffset.feature(COLUMN_TYPE_8BYTE)
        assert utf.schema.TocOffset.feature(COLUMN_TYPE_8BYTE)
        assert utf.schema.Files.feature(COLUMN_TYPE_4BYTE)

        s.TOC_BASELINE = min(utf.value('ContentOffset')[0], utf.value('TocOffset')[0])
        s.FILES = utf.value('Files')[0]

    def __toc(s, v):
        utf = v.utf

        assert utf.schema.DirName.feature(COLUMN_TYPE_STRING)
        assert utf.schema.FileName.feature(COLUMN_TYPE_STRING)
        assert utf.schema.FileSize.feature(COLUMN_TYPE_4BYTE)
        assert utf.schema.ExtractSize.feature(COLUMN_TYPE_4BYTE)
        assert utf.schema.FileOffset.feature(COLUMN_TYPE_8BYTE)
        assert utf.schema.ID.feature(COLUMN_TYPE_4BYTE)

        s.__OFFSET_ROW_MAP = {}
        for i in xrange(len(utf.rows)):
            s.__OFFSET_ROW_MAP[utf.value('FileOffset', i)[0] + s.TOC_BASELINE] = i

    def __itoc(s, v):
        utf = v.utf

        assert utf.schema.ID.feature(COLUMN_TYPE_4BYTE2)
        assert utf.schema.TocIndex.feature(COLUMN_TYPE_4BYTE2)

    def __etoc(s, v):
        utf = v.utf

        assert utf.schema.UpdateDateTime.feature(COLUMN_TYPE_8BYTE)
        assert utf.schema.LocalDir.feature(COLUMN_TYPE_STRING)

    __filter = {
        FRAME_CPK   : __cpk,
        FRAME_TOC   : __toc,
        FRAME_ITOC  : __itoc,
        FRAME_ETOC  : __etoc,
    }

    def __setitem__(s, k, v):
        if TableLibrary.__filter[k]:
            TableLibrary.__filter[k](s, v)
        dict.__setitem__(s, k, v)

    def fromoffset(s, offset):
        return Row(s[FRAME_TOC].utf, s.__OFFSET_ROW_MAP[offset])

class Row:
    """Shell to access row data"""

    def __init__(s, utf, rowid):
        s.utf = utf
        s.rowid = rowid

    def __getattr__(s, key):
        return s.utf.value(key, s.rowid)

from bitarray import bitarray

class CompressedIO:

    def __init__(s, indata):
        s.b = bitarray()
        s.b.frombytes(indata[::-1])
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
    yield 8

import time

class DeflateProgressIndicator:

    __INTERVAL = 0.1

    def __init__(s, insize, outsize):
        s.insize, s.outsize = insize, outsize
        s.tick = 0

    def feed(s, readptr, writeptr, force=False):
        if time.clock() - s.tick < DeflateProgressIndicator.__INTERVAL and not force:
            return
        print >>stderr, "                      0x%08x / 0x%08x % 6.2f%% => 0x%08x / 0x%08x % 6.2f%%\r" % (
                readptr, s.insize, float(readptr) * 100 / s.insize,
                writeptr, s.outsize, float(writeptr) * 100 / s.outsize),
        s.tick = time.clock()

from contextlib import nested

def __deflate(indata, size):
    MINIMAL_REFLEN = 3
    progress = DeflateProgressIndicator(len(indata), size)
    with nested(closing(CompressedIO(indata)), closing(StringIO())) as (f, out):
        while True:
            progress.feed(f.tell() >> 3, out.tell())
            bit = f.read01(1)
            if bit == '': 
                break
            if int(bit, 2):

                offset = f.readnum(13)
                refc = MINIMAL_REFLEN

                for lv in deflate_levels():
                    bits = f.read(lv)
                    refc += int(bits.to01(), 2)
                    if not bits.all():
                        break

                # DEBUG
                # curptr = out.tell()
                # refs = curptr - offset - MINIMAL_REFLEN
                # s = out.getvalue()[refs: min(refs + refc, curptr)]
                # print >>stderr, 'Control 1 0x%08x(-0x%04x-0x03)=0x%08x 0x%04x (0x%04x)%s' % (curptr, offset, refs, refc, len(s), repr(s))

                for i in xrange(refc):
                    original = out.tell()
                    # read referenced bytes
                    if out.tell() - offset - MINIMAL_REFLEN < 0:
                        ref = '\x00'
                    else:
                        out.seek(-offset-MINIMAL_REFLEN, 1)
                        ref = out.read(1)
                    # seek to the end
                    out.seek(0, 2)
                    assert out.tell() == original
                    out.write(ref)
            else:
                # verbatim byte
                b = f.readbyte()

                # DEBUG
                # print >>stderr, 'Control 0 0x%08x %s' % (out.tell(), repr(b))

                out.write(b)

        # Force flush a log
        progress.feed(f.tell() >> 3, out.tell(), True)
        return out.getvalue()[:size][::-1]

def uncompress(lib, dataframe):

    row = lib.fromoffset(dataframe.offset)

    dirname = row.DirName[0]

    (
        marker, uncompressed_size, datasize
    ) = unpack('<8sLL', dataframe.header)

    assert marker == 'CRILAYLA'

    assert datasize + 0x0100 == row.FileSize[0] - 0x10
    #      ^ Compressed Data    ^ Frame Size      ^ Frame Header
    #                 ^ Uncompressed Header 

    assert uncompressed_size + 0x0100 == row.ExtractSize[0]
    #      ^ Uncompressed Data Size      ^ Original File Size
    #                          ^ Uncompressed Header

    # Uncompress
    data = __deflate(dataframe.data[0], uncompressed_size)
    assert len(data) == uncompressed_size
    # if len(data) != uncompressed_size:
    #     print "WARNING! Extracted %s->%s DataSize mismatch with TOC record (%d <Uncompressed|TOC> %d -- %0.2f%%)" % \
    #             (row.DirName[0], row.FileName[0], len(data), uncompressed_size, float(len(data)) * 100 / uncompressed_size)
    #     # Padding with \x00
    #     data += '\x00' * (uncompressed_size - len(data))

    return dataframe.data[1] + data

####################
# Utility Fragment #
####################

import os, errno

def writefile(root, row, data):
    dirname = os.path.join(root, row.DirName[0])
    try:
        os.makedirs(dirname)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else: raise
    
    with open(os.path.join(dirname, row.FileName[0]), 'wb') as f:
        return f.write(data[:row.ExtractSize[0]])

################
# CLI Fragment #
################

COLUMN_TYPE_PRINT = {
    COLUMN_TYPE_DATA    : '0x%08x(0x%08x)',
    COLUMN_TYPE_STRING  : '%30s(0x%08x)',
    COLUMN_TYPE_FLOAT   : '%8.2f',
    COLUMN_TYPE_8BYTE   : '0x%016x',
    COLUMN_TYPE_4BYTE2  : '0x%08x',
    COLUMN_TYPE_4BYTE   : '0x%08x',
    COLUMN_TYPE_2BYTE2  : '0x%04x',
    COLUMN_TYPE_2BYTE   : '0x%04x',
    COLUMN_TYPE_1BYTE2  : '0x%02x',
    COLUMN_TYPE_1BYTE   : '0x%02x',
}

if __name__ == '__main__':

    LINE_WIDTH = 52

    def write_line(strline):
        print strline * LINE_WIDTH

    import argparse
    from sys import stderr

    parser = argparse.ArgumentParser(description='unpack a cpk archive')
    parser.add_argument('input', help='Input CPK file')
    parser.add_argument('-o', '--output-dir', 
            default='output', dest='output',
            help='Output directory (default "output")')
    args = parser.parse_args()

    infile = open(args.input, 'rb')

    print >>stderr, "Read %s..." % args.input

    STAT = {}

    for h, k in FRAME_HEADER_MAP:
        STAT[k] = 0

    frames = 0

    files = 0

    lib = TableLibrary()
    
    for frame in readframe(infile):

        # Statistic Information
        STAT[frame.typename] += 1
        frames += 1
        print >>stderr, "0x%010X Found Frame %-16s (0x%06X)\r" % \
                (frame.offset, frame.typename, len(frame.data[0])),

        if frame.typename in [FRAME_ZERO, FRAME_COPYRIGHT]: 
            # With no Data
            pass
        elif frame.typename in [FRAME_CPK, FRAME_TOC, FRAME_ITOC, FRAME_ETOC]:
            # If frame is the Index Frame

            # @UTF Table Format
            frame.utf = table = UTF(frame.data[0])

            # print schema(columns)

            write_line('=')
            print "Schema %s (%s)" % (table.name, frame.typename)
            write_line('-')
            for field in table.columns:
                print "\t%02x %30s(0x%08x)" % (field.typeid, field.name, field.nameoffset)
                if field.feature(COLUMN_STORAGE_CONSTANT):
                    print ("\t > " + COLUMN_TYPE_PRINT[field.fieldtype]) % (field.data)
            write_line('-')

            # for CPK header, print in K-V style

            if frame.typename in [FRAME_CPK]:
                # Vertical Table

                for i in xrange(len(table.columns)):
                    if table.columns[i].feature([
                        COLUMN_STORAGE_ZERO, 
                        COLUMN_STORAGE_CONSTANT,
                        ]):
                        continue
                    print '%30s' % table.columns[i].name,
                    print (COLUMN_TYPE_PRINT[table.columns[i].fieldtype] % table.rows[0][i]).strip()
            else:
                # Horizontal Table

                # print table header
                for i in xrange(len(table.columns)):
                    if table.columns[i].feature([
                        COLUMN_STORAGE_ZERO, 
                        COLUMN_STORAGE_CONSTANT,
                        ]):
                        continue
                    print '| ' + table.columns[i].name,
                print '|'

                # print table rows
                for row in table.rows:
                    for i in xrange(len(table.columns)):
                        if table.columns[i].feature([
                            COLUMN_STORAGE_ZERO, 
                            COLUMN_STORAGE_CONSTANT,
                            ]):
                            continue
                        print COLUMN_TYPE_PRINT[table.columns[i].fieldtype] % row[i],
                    print

            # Register frame to Library
            lib[frame.typename] = frame

        elif frame.typename in [FRAME_CRILAYLA]:
            # CRI Package

            files += 1

            row = lib.fromoffset(frame.offset)

            # DEBUG
            print >>stderr, ' ' * LINE_WIDTH + '\r',
            print >>stderr, '(% 4d/%d) %-30s 0x%08x -> 0x%08x (+0x0100=0x%08x)' % \
                    (files, lib.FILES, row.FileName[0], row.FileSize[0] - 0x110, row.ExtractSize[0] - 0x100, row.ExtractSize[0])

            writefile(args.output, row, uncompress(lib, frame))
        else:
            # Raw File Frame

            files += 1

            row = lib.fromoffset(frame.offset)

            assert row.FileSize[0] == row.ExtractSize[0]

            print >>stderr, ' ' * LINE_WIDTH + '\r',
            print >>stderr, '(% 4d/%d) %-30s 0x%08x' % \
                    (files, lib.FILES, row.FileName[0], row.FileSize[0])

            writefile(args.output, row, frame.data[0])

    print >>stderr, '=' * LINE_WIDTH
    print >>stderr, "Scanner Found %d Frames" % frames

    for h, k in FRAME_HEADER_MAP:
        print >>stderr, "%16s : %d" % (k, STAT[k])

    infile.close();

    exit(0);

