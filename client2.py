import argparse
import logging
import os
import random
import socket
import struct
import signal
import thread
import threading

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream, StreamClosedError
from tornado.tcpclient import TCPClient
from tornado.tcpserver import TCPServer
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

class AlarmException(Exception):
    pass

def alarmHandler(signum, frame):
    raise AlarmException

def nonBlockingRawInput(prompt='', timeout=2):
    signal.signal(signal.SIGALRM, alarmHandler)
    signal.alarm(timeout)
    try:
        text = raw_input(prompt)
        signal.alarm(0)
        return text
    except AlarmException:
        pass
        #print '\nPrompt timeout. Continuing...'
    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    return ''

@gen.coroutine
def client(port):
    while True:
        try:

            stream = yield tcp_client.connect('localhost', port)
            logging.info("Connected to %d", port)

            # Set TCP_NODELAY / disable Nagle's Algorithm.
            stream.set_nodelay(True)

            while True:
                print "*"
                msg = nonBlockingRawInput()
                if msg != '':
                    msg = str(port) + ': ' + msg
                    print "-"
                    length = _PACK_INT(len(msg))
                    yield stream.write(length + msg)
                yield gen.sleep(1)

        except StreamClosedError as exc:
            logger.error("Error connecting to %d: %s", port, exc)
            yield gen.sleep(1)

class MyServer(TCPServer):
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

        except StreamClosedError:
            logger.error("%s disconnected", address)

def main():
    loop = IOLoop.current()

    for peer in opts.peers:
        loop.spawn_callback(client, peer)

    server = MyServer()
    server.listen(opts.port)

    loop.start()

if __name__ == "__main__":
    main()