from struct import calcsize, pack, unpack
from array import array
from cStringIO import StringIO
from contextlib import closing, nested

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

def UTFChiper(data, c=0x5f, m=0x15):
    """Chiper for @UTF Table"""

    v = array('B', data)
    for i in xrange(len(v)):
        v[i] = v[i] ^ c & 0b11111111
        c = c * m & 0b11111111
    return (c, m, v.tostring())

class UTFTableIO:

    def __init__(s, istream=None, ostream=None, encrypted=False, key=(0x5f, 0x15)):
        s.istream = istream
        s.ostream = ostream
        s._istart = 0
        s._ostart = 0
        s.encrypted = encrypted

        if s.encrypted:
            # key used for encrypt
            (s.ikeyc, s.ikeym) = key
            (s.okeyc, s.okeym) = key

    def read(s, fmt=None, n=-1):
        if int == type(fmt):
            n = fmt
            fmt = None
        if fmt:
            return unpack(fmt, s.read(calcsize(fmt)))
        else:
            data = s.istream.read(n)
            if s.encrypted:
                (s.ikeyc, s.ikeym, data) = UTFChiper(data, s.ikeyc, s.ikeym)
            return data

    def write(s, b, fmt=None):
        if fmt:
            return s.write(pack(fmt, *b))
        else:
            if s.encrypted:
                (s.okeyc, s.okeym, b) = UTFChiper(b, s.okeyc, s.okeym)
            return s.ostream.write(b)

    def istart(s):
        s._istart = s.istream.tell()
        return s._istart

    def ostart(s):
        s._ostart = s.ostream.tell()
        return s._ostart

    def itell(s):
        return s.istream.tell() - s._istart

    def otell(s):
        return s.ostream.tell() - s._ostart

class AttributeDict(dict): 
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

class StringTable:
    """@UTF Table String Table"""

    def __init__(s):
        s.bytecounter = 0
        s.entry = []
        s.__map_stoo = {}
        s.__map_otos = {}

        # Default Value
        s.__getitem__('<NULL>')
    
    @classmethod
    def parse(cls, data):
        s = cls();
        init = data.strip('\x00').split('\x00')
        for entry in init:
            s.__getitem__(entry)    # Simply invoke __getitem__
        return s;

    def __getitem__(s, key):
        """string in offset out; offset in string out"""
        if type(key) == str:
            if s.__map_stoo.has_key(key):
                return s.__map_stoo[key]
            else:
                s.entry.append(key);
                s.__map_otos[s.bytecounter] = key
                s.__map_stoo[key] = s.bytecounter
                s.bytecounter += len(key) + 1 # For \x00 byte
                return s[key];
        else:
            # What if queried offset does not exists?
            return s.__map_otos[key]

    def dump(s, io):
        return io.write('\x00'.join(s.entry) + '\x00')

STRUCT_SCHEMA_DEF = '>BL'

class Column:
    """@UTF Table Column"""

    def __init__(s, utf):
        s.utf = utf

    @classmethod
    def parse(cls, utf, io):
        s = cls(utf)

        (typeid, s.nameoffset) = io.read(STRUCT_SCHEMA_DEF);

        s.storagetype = typeid & COLUMN_STORAGE_MASK
        s.fieldtype = typeid & COLUMN_TYPE_MASK

        if s.feature(COLUMN_STORAGE_CONSTANT):
            pattern = COLUMN_TYPE_MAP[s.fieldtype]
            if not pattern:
                raise Exception("Unknown Type 0x%02x" % s.fieldtype)
            col_data = io.read(pattern)
            s.const = col_data

        return s;

    def value(s, io, val=None):
        if not val:
            if s.feature(COLUMN_STORAGE_CONSTANT):
                val = s.const
            elif s.feature(COLUMN_STORAGE_ZERO):
                val = ()
            elif s.feature(COLUMN_STORAGE_PERROW):
                pattern = COLUMN_TYPE_MAP[s.fieldtype]
                if not pattern:
                    raise Exception("Unknown Type 0x%02x" % s.fieldtype)
                val = io.read(pattern)
            return val
        else:
            if s.feature(COLUMN_STORAGE_PERROW):
                pattern = COLUMN_TYPE_MAP[s.fieldtype]
                if not pattern:
                    raise Exception("Unknown Type 0x%02x" % s.fieldtype)
                return io.write((val), fmt=pattern);
            else:
                return None

    def feature(s, typeid):
        if type(typeid) == list:
            return s.storagetype in typeid or s.fieldtype in typeid or s.storagetype | s.fieldtype in typeid
        else:
            return s.storagetype == typeid or s.fieldtype == typeid or s.storagetype | s.fieldtype == typeid

    def translate(s):
        s.name = s.utf.string(s.nameoffset)
        if s.feature(COLUMN_STORAGE_CONSTANT | COLUMN_TYPE_STRING):
            s.const = s.utf.string(s.const[0])

    def dump(s, io):
        s.nameoffset = s.utf.string(s.name)

        typeid = s.storagetype | s.fieldtype
        io.write((typeid, s.nameoffset), fmt=STRUCT_SCHEMA_DEF)

        if s.feature(COLUMN_STORAGE_CONSTANT):
            pattern = COLUMN_TYPE_MAP[s.fieldtype]
            if not pattern:
                raise Exception("Unknown Type 0x%02x" % s.fieldtype)
            if s.feature(COLUMN_TYPE_STRING):
                io.write((s.utf.string(s.const), ), fmt=pattern)
            else:
                io.write(s.const, fmt=pattern)

class Row:
    """@UTF Table Data Row (Mutable)"""

    def __init__(s, utf):
        s.utf = utf
        s.row = []

    @classmethod
    def parse(cls, utf, io):
        s = cls(utf)

        for col in s.utf.cols:
            s.row.append((col, col.value(io)))

        return s

    def translate(s):
        row = []
        for v in s.row:
            if v[0].feature(COLUMN_STORAGE_PERROW | COLUMN_TYPE_STRING):
                v = (v[0], s.utf.string(v[1][0]))
            row.append(v)
        s.row = row

    def dump(s, io):
        for v in s.row:
            if v[0].feature(COLUMN_STORAGE_PERROW | COLUMN_TYPE_STRING):
                # Convert string to offset in string table
                v[0].value(io, (s.utf.string(v[1]), ));
            else:
                v[0].value(io, v[1]);

STRUCT_UTF_HEADER = '>4sL'
STRUCT_CONTENT_HEADER = '>LLLLHHL'

class UTFTable:
    """@UTF Table Structure"""

    def __init__(s):
        s.string_table = None
        s.rows = []
        s.cols = []

    @classmethod
    def parse(cls, f):
        s = cls();

        # @UTF Header Validation
        marker = f.read(4)
        if marker == '\x1F\x9E\xF3\xF5':
            s.encrypted = True
        elif marker == '@UTF':
            s.encrypted = False
        else:
            raise Exception("Invalid UTF Table Marker")
        f.seek(-4, 1);

        # IO Wrapper
        io = s.io = UTFTableIO(f, encrypted=s.encrypted)

        # @UTF Headers
        (
                s.marker, 
                s.table_size, 
        ) = io.read(STRUCT_UTF_HEADER)

        assert s.marker == '@UTF'

        # assert len(table_content) == s.table_size

        # Setup start flag for new section
        io.istart()

        # Table Headers
        (
                s.rows_offset, 
                s.string_table_offset, 
                s.data_offset, # always == s.table_size
                s.table_name_string, 
                s.column_length, 
                s.row_width, 
                s.row_length
        ) = io.read(STRUCT_CONTENT_HEADER)

        assert s.data_offset == s.table_size

        ## Columns

        while len(s.cols) < s.column_length:
            s.cols.append(Column.parse(s, io));

        assert io.itell() == s.rows_offset

        ## Rows

        while len(s.rows) < s.row_length:
            s.rows.append(Row.parse(s, io));

        assert io.itell() == s.string_table_offset

        ## String Table

        string_table_sz = s.table_size - s.string_table_offset

        s.string_table = StringTable.parse(io.read(string_table_sz))

        assert io.itell() == s.data_offset

        # Read values from string table
        s.translate()

        return s

    def string(s, v):
        return s.string_table[v]

    def translate(s):
        s.table_name = s.string(s.table_name_string)
        for c in s.cols:
            c.translate()
        for r in s.rows:
            r.translate()

    def dump(s, io=None):
        if not io:
            io = s.io

        if type(io) == file:
            io = UTFTableIO(ostream=io, encrypted=s.encrypted)

        s.table_name_string = s.string(s.table_name)
        s.column_length = len(s.cols)
        s.row_length = len(s.rows)

        s.row_width = 0

        cols_offset = calcsize(STRUCT_CONTENT_HEADER)

        with closing(StringIO()) as tf:
            iobuf = UTFTableIO(ostream=tf)

            # Dump Columns
            for c in s.cols:
                c.dump(iobuf)

                # Stat for row_width
                if c.feature(COLUMN_STORAGE_PERROW):
                    pattern = COLUMN_TYPE_MAP[c.fieldtype]
                    s.row_width += calcsize(pattern)

            s.rows_offset = cols_offset + iobuf.otell()

            # Dump Rows
            for r in s.rows:
                r.dump(iobuf)
        
            s.string_table_offset = cols_offset + iobuf.otell()

            # Dump String Table

            s.string_table.dump(iobuf)

            padding = ((0x10 - (iobuf.otell() + cols_offset + calcsize(STRUCT_UTF_HEADER)) % 0x10) % 0x10) * '\x00'
            iobuf.write(padding)

            s.data_offset = cols_offset + iobuf.otell()
            s.table_size = s.data_offset

            io.write(('@UTF', s.table_size), fmt=STRUCT_UTF_HEADER)
            io.ostart()
            io.write((
                s.rows_offset, 
                s.string_table_offset, 
                s.data_offset, # always == s.table_size
                s.table_name_string, 
                s.column_length, 
                s.row_width, 
                s.row_length
            ), fmt=STRUCT_CONTENT_HEADER)
            io.write(tf.getvalue())

