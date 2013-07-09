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

def UTFChiper(data):
    """Chiper for @UTF Table"""

    c, m = (0x5f, 0x15)
    v = array('B', data)
    for i in xrange(len(v)):
        v[i] = v[i] ^ c & 0b11111111
        c = c * m & 0b11111111
    return v.tostring()

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

    def dump(s):
        return '\x00'.join(s.entry) + '\x00';

    __str__ = dump

class Column:
    """@UTF Table Column"""

    def __init__(s, utf):
        s.utf = utf

    @classmethod
    def parse(cls, utf, data):
        pass

    def feature(s, typeid):
        pass

    def dump(s):
        pass

    __str__ = dump

class Row(AttributeDict):
    """@UTF Table Data Row (Mutable)"""

    def __init__(s, utf):
        pass

    @classmethod
    def parse(cls, utf, data):
        pass

    def dump(s):
        pass

    __str__ = dump

class UTFTable:
    """@UTF Table Structure"""

    def __init__(s):
        s.string_table = None
        s.rows = None
        s.cols = None

    @classmethod
    def parse(s, data):
        pass

    def dump(s):
        pass

    __str__ = dump
