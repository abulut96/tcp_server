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
from tornado.options import options as tornado_options
parser = argparse.ArgumentParser()
parser.add_argument("port", type=int, help="port to listen on")
parser.add_argument("peers", type=int, nargs="+", help="peers' ports")
opts = parser.parse_args()

# This is just to configure Tornado logging.
tornado_options.parse_command_line()
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.INFO)

# Cache this struct definition; important optimization.
int_struct = struct.Struct("<i")
_UNPACK_INT = int_struct.unpack
_PACK_INT = int_struct.pack

tcp_client = TCPClient()

@gen.coroutine
class MyClient(TCPClient):
    def connect(port):
        while True:
            try:
                stream = yield tcp_client.connect('localhost', port)
                logging.info("Connected to %d", port)

                # Set TCP_NODELAY / disable Nagle's Algorithm.
                stream.set_nodelay(False)

                while True:
                    msg = yield stream.read_until("\n")
                    yield stream.write(msg)
                    length = _PACK_INT(len(msg))
                    yield stream.write(length + msg)
                    yield gen.sleep(3)

            except StreamClosedError as exc:
                logger.error("Error connecting to %d: %s", port, exc)
                yield gen.sleep(5)


def main():
    client = MyClient()
    client.connect(opts.port)
    IOLoop.current().start()

if __name__ == "__main__":
    main()