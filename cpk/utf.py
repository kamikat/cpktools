from io import SEEK_SET, SEEK_CUR, SEEK_END
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

# Struct Definition

STRUCT_COLUMN_SCHEMA    = '>BL'
STRUCT_COLUMN_DATA      = {
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

STRUCT_TABLE_HEADER = '>4sL'
STRUCT_BODY_HEADER = '>LLLLHHL'

def keyset(c, m):
    f = c
    yield c
    c = c * m & 0b11111111
    while not c == f:
        yield c
        c = c * m & 0b11111111

class UTFChiper:

    """Chiper for @UTF Table"""

    def __init__(s, c=0x5f, m=0x15):

        # Configure encrypt/decrypt key (balanced)
        s.codes = [x for x in keyset(c, m)]
        s.pos = 0
        s.m = m

    def code(s, data):

        """Encrypt/Decrypt data"""

        v = array('B', data)

        for i in xrange(len(v)):
            v[i] = v[i] ^ s.codes[s.pos] & 0b11111111
            s.seek(1, SEEK_CUR)

        return v.tostring()

    def seek(s, offset, whence = SEEK_SET):

        if whence == SEEK_SET:
            s.pos = offset % len(s.codes)

        if whence == SEEK_CUR:
            s.pos = (offset + s.pos) % len(s.codes)

    def key(s):

        return (s.codes[s.pos], s.m)

class UTFTableIO:

    """@UTF Table IO Helper"""

    def __init__(s, stream, encrypted=False, key=(0x5f, 0x15)):

        """
        Create a wrapper class for stream provided
        """

        (s.stream, s.encrypted) = (stream, encrypted)

        # Create chiper instance for encrypted stream
        s.chiper = UTFChiper(*key) if s.encrypted else None

        # Record start position of current stream
        s.spos = stream.tell()

    def read(s, fmt=None, n=-1):

        """Read data from stream, if `fmt' string specified, will read length of the format string"""

        # Shift arguments
        if int == type(fmt):
            n = fmt
            fmt = None

        if fmt:
            
            return unpack(fmt, s.read(calcsize(fmt)))

        else:

            data = s.stream.read(n)

            # Decrypt data from stream
            if s.encrypted:
                data = s.chiper.code(data)

            return data

    def write(s, b, fmt=None):

        """Write data to stream, `b' can be string or tuple with `fmt' specified"""

        if fmt:

            return s.write(pack(fmt, *b))

        else:

            # Encrypt data to stream
            if s.encrypted:
                b = s.chiper.code(b)

            return s.stream.write(b)

    def tell(s):

        return s.stream.tell() - s.spos

    def seek(s, offset, whence = SEEK_SET):

        # Seek the chiper
        if s.chiper:
            s.chiper.seek(offset, whence)

        if whence == SEEK_SET:
            return s.stream.seek(offset + s.spos)

        return s.stream.seek(offset, whence)

class StringTable:

    """@UTF Table String Table"""

    def __init__(s):

        s.bytecounter = 0

        s.entry = []

        s._map_stoo = {}
        s._map_otos = {}

        # Default Value
        s.__getitem__('<NULL>')
    
    @classmethod
    def parse(cls, data):

        s = cls();

        init = data.strip('\x00').split('\x00')

        for entry in init:
            s.__getitem__(entry)    # Invoke __getitem__ to register mapping

        return s;

    def __getitem__(s, key):

        """Given string return offset; Given offset return string"""

        if type(key) == str:

            if s._map_stoo.has_key(key):
                
                return s._map_stoo[key]

            else:

                # A new string entry
                s.entry.append(key);

                # Register to mapping
                s._map_otos[s.bytecounter] = key
                s._map_stoo[key] = s.bytecounter

                s.bytecounter += len(key) + 1 # For \x00 byte

                return s[key];

        else:

            if s._map_otos.has_key(key):

                return s._map_otos[key]

            else:
                
                raise Exception("Cannot find string entry at 0x%x" % (key))

    def dump(s, io):

        return io.write('\x00'.join(s.entry) + '\x00')

class StringHelper(object):

    """
    Helper to resolve @UTF Table element's string value

    By specifying 

        class.__escape__ = <list of names> 
        self._escape_ = <list of names> 

    attributes with the name in list will be automatically escaped according to 
    StringTable, all values set to the attribute will also be mapped to StringTable
    automatically.
    """

    def __requireescape(s, attr):

        if attr.startswith('_'):
            
            return False

        clz = s.__class__

        r1 = (attr in clz.__escape__) if '__escape__' in dir(clz) else False
        r2 = (attr in s._escape_) if '_escape_' in dir(s) else False

        return r1 or r2

    def __getattr__(s, attr):

        if s.__requireescape(attr):

            val = object.__getattribute__(s, '_offset_' + attr)
            val = s.string(val)

        else:

            val = object.__getattribute__(s, attr)

        return val

    def __setattr__(s, attr, val):

        if s.__requireescape(attr):

            if str == type(val):
                val = s.string(val)

            # Set origin value to private variable with same name 
            return s.__setattr__('_offset_' + attr, val)

        return object.__setattr__(s, attr, val)

    def string(s, val):

        """Convert between string and offset"""

        if not 'utf' in dir(s):
            raise Exception("@UTF Table object must be specified")

        return s.utf.string(val)

class Column(StringHelper):

    """@UTF Table Column Schema Definition"""

    __escape__ = [ 'name' ]

    def __init__(s, utf, name, storage, datatype):

        (s.utf, s.name, s.storage, s.datatype) = (utf, name, storage, datatype)

    @classmethod
    def parse(cls, utf, io):

        (typeid, name) = io.read(STRUCT_COLUMN_SCHEMA)

        (storage, datatype) = (typeid & COLUMN_STORAGE_MASK, typeid & COLUMN_TYPE_MASK)

        s = cls(utf, name, storage, datatype)

        # Read Constant
        s.const = io.read(s.pattern()) if s.be(COLUMN_STORAGE_CONSTANT) else None

        return s

    def pattern(s):

        """Get read/write pattern for current Column data"""

        pattern = STRUCT_COLUMN_DATA[s.datatype]

        if not pattern:
            raise Exception("Unknown Type 0x%02x" % s.fieldtype)

        return pattern

    def read(s, io):

        """Read a value defined by the Column, return a tuple"""

        if s.be(COLUMN_STORAGE_CONSTANT):

            # As for string constant, a pointer to StringTable is returned
            return s.const

        elif s.be(COLUMN_STORAGE_ZERO):

            return ()

        elif s.be(COLUMN_STORAGE_PERROW):

            return io.read(s.pattern())

    def write(s, io, val):

        """Write a value defined by the Column to a UTFTableIO stream"""

        if s.be(COLUMN_STORAGE_CONSTANT):

            pass # raise Exception("Unable to write to CONSTANT STORAGE Column `%s'" % s.name)

        elif s.be(COLUMN_STORAGE_ZERO):

            pass # raise Exception("Unable to write to ZERO STORAGE Column `%s'" % s.name)

        elif s.be(COLUMN_STORAGE_PERROW):

            return io.write(val, s.pattern())

    def be(s, typeid):

        """Check the Column type to have any feature, return True/False"""

        if type(typeid) == list:

            return s.storage in typeid or s.datatype in typeid or s.storage | s.datatype in typeid

        else:

            return s.storage == typeid or s.datatype == typeid or s.storage | s.datatype == typeid

    def __repr__(s):
        return '"' + s.name + '"'

    def dump(s, io):

        io.write((s.storage | s.datatype, s._offset_name), STRUCT_COLUMN_SCHEMA)

        if s.be(COLUMN_STORAGE_CONSTANT):
            io.write(s.const, s.pattern())

class Row(StringHelper):

    """@UTF Table Data Row (Mutable)"""

    def __init__(s, utf):

        s.utf = utf

        # Configure StringHelper
        s._escape_ = map(
                lambda x: x.name,
                filter(
                    lambda x: x.be([
                        COLUMN_TYPE_STRING | COLUMN_STORAGE_PERROW, 
                        COLUMN_TYPE_STRING | COLUMN_STORAGE_CONSTANT
                        ]), 
                    s.utf.cols
                )
            )

    @classmethod
    def parse(cls, utf, io):

        s = cls(utf)

        for col in s.utf.cols:

            val = col.read(io)

            # Set value as instance attribute
            s.__setattr__(col.name, val)

        return s

    def dump(s, io):

        for col in s.utf.cols:

            if col.name in s._escape_:
                val = s.__getattr__('_offset_' + col.name)
            else:
                val = s.__getattr__(col.name)

            col.write(io, val);

    __getitem__ = StringHelper.__getattr__
    __setitem__ = StringHelper.__setattr__

class UTFTable(StringHelper):
    """@UTF Table Structure"""

    __escape__ = [ 'table_name' ]

    def __init__(s):

        # Referenced from StringHelper
        s.utf = s

        # New instance of StringTable
        s.string_table = StringTable()

        # Initialize rows and cols list
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

        # Reset the read pointer
        f.seek(-len(marker), SEEK_CUR);

        # IO Wrapper
        io = s.io = UTFTableIO(f, encrypted=s.encrypted)

        # @UTF Headers
        (
                s.marker, 
                s.table_size, 
        ) = io.read(STRUCT_TABLE_HEADER)

        assert s.marker == '@UTF'

        # Enter table body
        io = UTFTableIO(io)

        # Table Headers

        io.seek(0)

        (
                s.rows_offset, 
                s.string_table_offset, 
                s.data_offset, # always == s.table_size
                s.table_name, 
                s.column_length, 
                s.row_width, 
                s.row_length
        ) = io.read(STRUCT_BODY_HEADER)

        assert s.data_offset == s.table_size

        ## END

        ## String Table

        io.seek(s.string_table_offset)

        string_table_sz = s.table_size - s.string_table_offset

        s.string_table = StringTable.parse(io.read(string_table_sz))

        assert io.tell() == s.data_offset

        ## END

        ## Columns

        io.seek(calcsize(STRUCT_BODY_HEADER))

        while len(s.cols) < s.column_length:
            s.cols.append(Column.parse(s, io));

        assert io.tell() == s.rows_offset

        ## END

        ## Rows

        io.seek(s.rows_offset)

        while len(s.rows) < s.row_length:
            s.rows.append(Row.parse(s, io));

        assert io.tell() == s.string_table_offset

        ## END

        return s

    def string(s, v):

        if tuple == type(v):
            v = v[0]

        return s.string_table[v]

    def __len__(s):

        # Return record count
        return len(s.rows)

    def dump(s, io):

        if type(io) == file:
            io = UTFTableIO(io, encrypted=s.encrypted)

        table_name = s._offset_table_name

        s.column_length = len(s.cols)
        s.row_length = len(s.rows)

        s.row_width = 0

        body_offset = calcsize(STRUCT_BODY_HEADER)

        f = StringIO()
        iobuf = UTFTableIO(f)

        # Dump Columns
        for c in s.cols:
            c.dump(iobuf)

            # Stat for row_width
            if c.be(COLUMN_STORAGE_PERROW):
                s.row_width += calcsize(c.pattern())

        # Dump Rows
        s.rows_offset = body_offset + iobuf.tell()

        for r in s.rows:
            r.dump(iobuf)
    
        # Dump String Table
        s.string_table_offset = body_offset + iobuf.tell()

        s.string_table.dump(iobuf)

        # Calculate padding (including STRUCT_TABLE_HEADER)
        table_dry_sz = calcsize(STRUCT_TABLE_HEADER) + body_offset + iobuf.tell()
        padding = ((0x10 - table_dry_sz % 0x10) % 0x10) * '\x00'
        iobuf.write(padding)

        # Calculate table size
        s.table_size = body_offset + iobuf.tell()
        s.data_offset = s.table_size

        # Write @UTF Table
        io.write(('@UTF', s.table_size), STRUCT_TABLE_HEADER)
        io.write((
            s.rows_offset, 
            s.string_table_offset, 
            s.data_offset, # always == s.table_size
            s._offset_table_name, 
            s.column_length, 
            s.row_width, 
            s.row_length
        ), STRUCT_BODY_HEADER)
        io.write(f.getvalue())

