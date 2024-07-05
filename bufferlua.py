'''
Replicates how Luau handles Binary Files and implements key luau bit32 module functions
'''

import math
import struct

def bor(*args):
    result = 0
    for number in args:
        result |= number
    return result

def ords(s, start=None, end=None):   
    '''
    Python implementation of string.byte
    ord() func that supports multiple letters
    ''' 
    if end == None:
        end = len(s) + 1

    array = [0] * (end - start)

    c = 0
    for char in s[start:end]:
        array[c] = char
        c += 1

    return array

def extract(number, position, width):
    '''
    Python implementation of bit32.extract
    '''
    mask = ((1 << width) - 1) << position
    return (number & mask) >> position

class Buffer():
    def __init__(self, content: bytes):
        self.content_len = len(content)
        self.buffer_len = self.content_len * 8
        self.buffer_index = 0
        self.buffer = [0] * int(self.content_len / 2)
        self.buffer_n = math.ceil(self.content_len / 4) - 2

        for i in range(math.floor(self.content_len / 4)):
            a, b, c, d = ords(content, i * 4, i * 4 + 4)
            self.buffer[i] = bor(a, b * 256, c * 65536, d * 16777216)

        for i in range(self.content_len % 4): # this is probably very wrong
            b = ords(content, (self.buffer_n - 1) * 4 + i + 1)
            self.buffer[self.buffer_n] = bor(self.buffer[self.buffer_n], b[0] * 256 ** i)
    
    def __patch_overflow(self):
        if self.buffer_index > self.buffer_len:
            self.buffer_len = self.buffer_index

    def skip(self, size: int):
        '''
        Sets pointer + size (in bytes)
        '''
        if size > 0:
            self.buffer_index += size * 8
            self.__patch_overflow()
    
    def read_unit(self, size: int):
        '''
        Read current pointer's and returns unsigned int
        '''

        if size == 0:
            return 0
        
        i = self.buffer_index >> 5
        u = self.buffer_index % 32

        self.buffer_index += size
        self.__patch_overflow()

        if u == 0 and size == 32:
            return self.buffer[i]
        
        f = 32 - u
        r = f - size

        if r >= 0:
            return extract(self.buffer[i], u, size)
        
        cur = extract(self.buffer[i], u, f)
        nex = extract(self.buffer[i + 1], 0, -r)
        return bor(cur, nex << f)
    
    def read_mul_units(self, count: int):
        '''
        Read multiple units at pointer with given count
        '''
        return (self.read_unit(8) for i in range(count))
    
    def read_bytes(self, size: int):
        '''
        Read bytes as string
        '''
        return "" if size == 0 else "".join(chr(self.read_unit(8)) for i in range(size))
    
    def read_float(self, size: int):
        '''
        Reads float
        '''
        s = self.read_bytes(math.floor(size / 8))
        b = bytes(s, 'latin1')
        return struct.unpack("<f" if size == 32 else "<d", b)
    
    def read_int(self, size: int):
        '''
        Reads signed int
        '''
        if size == 0:
            return 0
        
        v = 0

        if size <= 32:
            v = self.read_unit(size)
        else:
            v = self.read_unit(32) + self.read_unit(size - 32) * 2 ** 32
        
        n = 2 ** size
        v %= n

        if v >= n / 2:
            return v - n
        else:
            return v
        
    def read_vector3(self):
        return (
            self.read_float(32),
            self.read_float(32),
            self.read_float(32)
        )
    
    def read_vector2(self):
        return (
            self.read_float(32),
            self.read_float(32)
        )