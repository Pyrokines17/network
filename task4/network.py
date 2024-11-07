from queue import LifoQueue
from queue import Queue

from snakes_pb2 import *

import threading

import struct
import socket

MULTICAST_GROUP = '239.192.0.4'
MULTICAST_PORT = 9192

class Binder:
    def __init__(self):
        self.multicast_socket = self.setup_multicast_socket()
        self.other_socket = self.setup_other_socket()

        self.mulMessages = LifoQueue()
        self.lock = threading.Lock()
        self.messages = Queue()

        self.other_thread = threading.Thread(target=self.listen_other)
        self.multicast_thread = threading.Thread(target=self.listen_multicast)

    def setup_multicast_socket(self):
        multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        multicast_socket.bind(('', MULTICAST_PORT))
        multicast_socket.settimeout(0.2)

        multicast_group = socket.inet_aton(MULTICAST_GROUP)
        mreq = struct.pack('4sL', multicast_group, socket.INADDR_ANY)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        return multicast_socket

    def setup_other_socket(self):
        other_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        other_socket.settimeout(0.2)
        return other_socket

    def send_multicast(self, message):
        multicast_addr = (MULTICAST_GROUP, MULTICAST_PORT)
        self.multicast_socket.sendto(message, multicast_addr)

    def send_other(self, message, address):
        self.other_socket.sendto(message, address)

    def listen_multicast(self):
        while self.runningMul:
            try:
                data, address = self.multicast_socket.recvfrom(1024)
                gameMsg = GameMessage()
                gameMsg.ParseFromString(data)
                #print(f'Multicast received from {address}:\n{gameMsg}')
                with self.lock:
                    self.mulMessages.put((gameMsg, address))
            except socket.timeout:
                pass
            except socket.error as e:
                print(f'Multicast error: {e}')

        self.multicast_socket.close()

    def listen_other(self):
        while self.running:
            try:
                data, address = self.other_socket.recvfrom(1024)
                gameMsg = GameMessage()
                gameMsg.ParseFromString(data)
                #print(f'Other received from {address}:\n{gameMsg}')
                with self.lock:
                    self.messages.put((gameMsg, address))
            except socket.timeout:
                pass
            except socket.error as e:
                print(f'Other error: {e}')

        self.other_socket.close()

    def start(self):
        self.running = True
        self.runningMul = True
        self.other_thread.start()
        self.multicast_thread.start()
                
    def stop(self):
        with self.lock:
            self.running = False
    
    def stopMul(self):
        with self.lock:
            self.runningMul = False

    def process_multicast(self):
        with self.lock:
            while not self.mulMessages.empty():
                data, address = self.mulMessages.get()
                print(f"Processing multicast from {address}: {data}")

    def process_messages(self):
        with self.lock:
            while not self.messages.empty():
                data, address = self.messages.get()
                print(f"Processing message from {address}: {data}")

    def get_uniq_mulMessages(self):
        with self.lock:
            uniq_messages = []

            while not self.mulMessages.empty():
                data, address = self.mulMessages.get()

                if data not in uniq_messages:
                    uniq_messages.append((data, address))

            return uniq_messages
        