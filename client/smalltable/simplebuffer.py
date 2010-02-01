'''
This is an implementation of a simple buffer. SimpleBuffer just handles
a string of bytes. The clue, is that you can pop data from the beginning
and append data to the end.

It's ideal to use as a network buffer, from which you send data to the socket.
Use this to avoid concatenating or splitting large strings.
'''
import os
import socket
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class SimpleBuffer:
    """
    >>> b = SimpleBuffer("abcdef")
    >>> b.read_and_consume(3)
    'abc'
    >>> b.write(None, '')
    >>> b.read(0)
    ''
    >>> repr(b)
    "<SimpleBuffer of 3 bytes, 6 total size, 'def'>"
    >>> str(b)
    "<SimpleBuffer of 3 bytes, 6 total size, 'def'>"
    >>> b.flush()
    >>> b.read(1)
    ''
    """
    buf = None
    offset = 0
    size = 0

    def __init__(self, data=None):
        self.buf = StringIO.StringIO()
        if data is not None:
            self.write(data)
        self.buf.seek(0, os.SEEK_END)

    def write(self, *data_strings):
        ''' Append given strings to the buffer. '''
        for data in data_strings:
            if not data:
                continue
            self.buf.write(data)
            self.size += len(data)

    def read(self, size=None):
        ''' Read the data from the buffer, at most 'size' bytes.

        >>> s = SimpleBuffer()
        >>> s.write('abcde')
        >>> s.read(1)
        'a'
        >>> s.read()
        'abcde'
        '''
        if size is 0:
            return ''

        self.buf.seek(self.offset)

        if size is None:
            data = self.buf.read()
        else:
            data = self.buf.read(size)

        self.buf.seek(0, os.SEEK_END)
        return data

    def consume(self, size):
        ''' Move pointer and discard first 'size' bytes.

        >>> s = SimpleBuffer()
        >>> s.write('a'*65537)
        >>> s.consume(65537)
        >>> s.read()
        ''
        '''
        self.offset += size
        self.size -= size
        # GC old StringIO instance and free memory used by it.
        if self.size == 0 and self.offset > 65536:
            self.buf.close()
            del self.buf
            self.buf = StringIO.StringIO()
            self.offset = 0

    def read_and_consume(self, size):
        ''' Read up to 'size' bytes, also remove it from the buffer. '''
        assert(self.size >= size)
        data = self.read(size)
        self.consume(size)
        return data

    def send_to_socket(self, sd):
        ''' Faster way of sending buffer data to socket 'sd'. '''
        self.buf.seek(self.offset)
        try:
            r = sd.send( self.buf.read() )
        except socket.error, (e, msg):
            if e == 11: # errno.EAGAIN
                return
            raise
        self.buf.seek(0, os.SEEK_END)
        self.offset += r
        self.size -= r
        if self.offset > 524288 and self.size == 0:
            self.consume(0)
        return r

    def recv_from_socket(self, sd):
        r = 524288
        s = 0
        while r == 524288:
            data = ''
            try:
                data = sd.recv(524288)
            except socket.error, (e, msg):
                if e == 11: # errno.EAGAIN
                    return
                raise
            self.write(data)
            r = len(data)
            #import sys
            #print >> sys.stderr, ("received %r" % (data,))
            s += r
        return s

    def flush(self):
        ''' Remove all the data from buffer. '''
        self.consume(self.size)

    def __nonzero__(self):
        ''' Are we empty?

        >>> s = SimpleBuffer()
        >>> True if s else False
        False
        '''
        return True if self.size else False

    def __len__(self):
        '''
        >>> s = SimpleBuffer()
        >>> len(s)
        0
        '''
        return self.size

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<SimpleBuffer of %i bytes, %i total size, %r%s>' % \
                    (self.size, self.size + self.offset, self.read(16), '...' if self.size > 16 else '')
