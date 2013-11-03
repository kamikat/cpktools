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

STRUCT_UTF_HEADER = '>4sL'
STRUCT_CONTENT_HEADER = '>LLLLHHL'

class UTFChiper:

    """Chiper for @UTF Table"""

    def __init__(s, c=0x5f, m=0x15):

        # Configure encrypt/decrypt key (balanced)
        (s.c, s.m) = (c, m)

    def code(s, data):

        """Encrypt/Decrypt data"""

        v = array('B', data)

        for i in xrange(len(v)):
            v[i] = v[i] ^ s.c & 0b11111111
            s.c = s.c * s.m & 0b11111111

        return v.tostring()

class UTFTableIO:

    """@UTF Table IO Helper"""

    def __init__(s, stream=None, encrypted=False, key=(0x5f, 0x15)):

        (s.stream, s.encrypted) = (stream, encrypted)

        # Create chiper instance for encrypted stream
        s.chiper = UTFChiper(*key) if s.encrypted else None

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

        return s.stream.tell()

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
            s.__getitem__(entry)    # Invoke __getitem__ to register mapping

        return s;

    def __getitem__(s, key):

        """Given string return offset; Given offset return string"""

        if type(key) == str:

            if s.__map_stoo.has_key(key):
                
                return s.__map_stoo[key]

            else:

                # A new string entry
                s.entry.append(key);

                # Register to mapping
                s.__map_otos[s.bytecounter] = key
                s.__map_stoo[key] = s.bytecounter

                s.bytecounter += len(key) + 1 # For \x00 byte

                return s[key];

        else:

            if s.__map_otos.has_key(key):

                return s.__map_otos[key]

            else:
                
                raise Exception("Cannot find string entry at %x" % key)

    def dump(s, io):

        return io.write('\x00'.join(s.entry) + '\x00')

class StringHelper(object):

    """
    Helper to resolve @UTF Table element's string value

    By specifying 

        class.__escape__ = <list of names> 

    attributes with the name in list will be automatically escaped according to 
    StringTable, all values set to the attribute will also be mapped to StringTable
    automatically.
    """

    def __requireescape(s, attr):

        if attr.startswith('__'):
            
            return False

        clz = s.__class__

        if list == type(clz.__escape__):

            return attr in clz.__escape__ or attr in s.__escape__

    def __getattr__(s, attr):

        val = object.__getattr__(s, attr)

        if s.__requireescape(attr):

            val = s.string(val)

        return val

    def __setattr__(s, attr, val):

        if s.__requireescape(attr):

            if str == type(val):
                val = s.string(val)

            # Set a copy of origin value to private variable with same name 
            s.__setattr__('__' + attr, val)

        return object.__setattr__(s, attr, val)

    def string(s, val):

        """Convert between string and offset"""

        if !s.utf:
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

            raise Exception("Unable to write to CONSTANT STORAGE Column `%s'" % s.name)

        elif s.be(COLUMN_STORAGE_ZERO):

            raise Exception("Unable to write to ZERO STORAGE Column `%s'" % s.name)

        elif s.be(COLUMN_STORAGE_PERROW):

            return io.write((val), s.pattern())

    def be(s, typeid):

        """Check the Column type to have any feature, return True/False"""

        if type(typeid) == list:

            return s.storage in typeid or s.datatype in typeid or s.storage | s.datatype in typeid

        else:

            return s.storage == typeid or s.datatype == typeid or s.storage | s.datatype == typeid

    def dump(s, io):

        io.write((typeid, s.__name), STRUCT_COLUMN_SCHEMA)

        if s.be(COLUMN_STORAGE_CONSTANT):
            io.write(s.const, s.pattern())

class Row(StringHelper):

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
            if v[0].be(COLUMN_STORAGE_PERROW | COLUMN_TYPE_STRING):
                v = (v[0], s.utf.string(v[1][0]))
            row.append(v)
        s.row = row

    def dump(s, io):
        for v in s.row:
            if v[0].be(COLUMN_STORAGE_PERROW | COLUMN_TYPE_STRING):
                # Convert string to offset in string table
                v[0].value(io, (s.utf.string(v[1]), ));
            else:
                v[0].value(io, v[1]);

class UTFTable(StringHelper):
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
                if c.be(COLUMN_STORAGE_PERROW):
                    pattern = STRUCT_COLUMN_DATA[c.fieldtype]
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

            io.write(('@UTF', s.table_size), STRUCT_UTF_HEADER)
            io.ostart()
            io.write((
                s.rows_offset, 
                s.string_table_offset, 
                s.data_offset, # always == s.table_size
                s.table_name_string, 
                s.column_length, 
                s.row_width, 
                s.row_length
            ), STRUCT_CONTENT_HEADER)
            io.write(tf.getvalue())

