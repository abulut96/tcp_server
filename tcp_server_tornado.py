#!/usr/bin/env python

import argparse
import logging
import os
import random
import socket
import struct

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream, StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
from tornado.options import options as tornado_options

parser = argparse.ArgumentParser()
parser.add_argument("port", type=int, help="port to listen on")
# parser.add_argument("peers", type=int, nargs="+", help="peers' ports")
opts = parser.parse_args()

# This is just to configure Tornado logging.
tornado_options.parse_command_line()
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.INFO)

# Cache this struct definition; important optimization.
int_struct = struct.Struct("<i")
_UNPACK_INT = int_struct.unpack
_PACK_INT = int_struct.pack

class MyServer(TCPServer):
    @gen.coroutine
    def server_reply(self, stream):
        reply = "Merhaba. Tcp serverina hos geldiniz."
        length2 = _PACK_INT(len(reply))
        yield stream.write(length2 + reply)

    @gen.coroutine
    def handle_stream(self, stream, address):
        logging.info("Connection from peer")
        try:
            while True:
                # Read 4 bytes.
                header = yield stream.read_bytes(4)

                # Convert from network order to int.
                length = _UNPACK_INT(header)[0]

                msg = yield stream.read_bytes(length)
                logger.info('"%s"' % msg.decode())

                del msg  # Dereference msg in case it's big.

                yield self.server_reply(stream)

        except StreamClosedError:
            logger.error("%s disconnected", address)

def main():
    server = MyServer()
    server.listen(opts.port)
    IOLoop.current().start()

if __name__ == "__main__":
    main()