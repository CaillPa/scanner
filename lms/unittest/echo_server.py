import socket
import threading
from LMS1xx import scanCfg

class EchoServer():
    """
        Simple mono-client server class used for unit testing of LMS1xx class
    """
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.__running = False
        self.__thread = None
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.ip, self.port))

    def start(self):
        if not self.__running:
            print('DEBUG: Starting echo server')
            self.__thread = ServerThread(self.server_socket)
            self.__thread.start()
            self.__running = True

    def stop(self):
        print('DEBUG: Stopping echo server')
        self.__thread.stop()
        self.__running = False

    def getbuf(self):
        return self.__thread.getbuf()

class ServerThread(threading.Thread):
    def __init__(self, server_socket):
        threading.Thread.__init__(self)
        self.__buf = ''
        self.__running = False
        self.server_socket = server_socket

    def run(self):
        print("DEBUG: Starting server's main thread")
        self.__running = True
        while self.__running:
            self.server_socket.listen()
            try:#because killing the server raises an error
                client, _ = self.server_socket.accept()
            except OSError:
                break
            self.__buf = client.recv(128)
            cmd = self.__buf.split(b'\x20')[1][0:-1].decode()
            if cmd == 'STlms':
                buf = bytearray(b'\x02sRA STlms\x00\x04'+bytes(36))
                self.__buf = b'\x04'
                client.send(buf)
            elif cmd == 'SetAccessMod':
                print('test_login(): ', self.__buf)
                client.send(self.__buf)
            elif cmd == 'LMPscancfg':
                buf = bytearray(b'\x02sRA LMPscancfg \x00\x00\x13\x88 '+\
                                b'\x00\x01 \x00\x00\x13\x88 \xFF\xF9\x22\x30 '+\
                                b'\x00\x22\x55\x10\x03')
                client.send(buf)
            elif cmd == 'mLMPsetscancfg':
                cfg = scanCfg()
                buf = self.__buf.split(b'\x20')
                cfg.scaningFrequency = buf[2]
                cfg.angleResolution = buf[4]
                cfg.startAngle = buf[5]
                cfg.startAngle = buf[6]
                client.send(self.__buf)
                self.__buf = cfg

            elif cmd == 'LMPoutputRange':
                buf = bytearray(b'\x02sRA LMPoutputRange \x00\x01 \x13\x88 '+\
                                b'\xFF\xF9\x22\x30 \x00\x22\x55\x10\x03')
                client.send(buf)

            elif cmd == 'LMDscandat':
                start = self.__buf.split(b'\x20')[2][0:-1]
                client.send(self.__buf)
                self.__buf = start

            else:
                client.send(self.__buf)

            client.close()

        self.server_socket.close()
        print("DEBUG: Server's main thread stopped")

    def stop(self):
        print("DEBUG: Stopping server's main thread")
        self.__running = False
        self.server_socket.shutdown(socket.SHUT_RDWR)
        self.server_socket.close()

    def getbuf(self):
        return self.__buf
