import socket
import random
import threading
import time
import copy
import math
import sys

class sender(object):
    def __init__(self, rhost, rport, fname, MWS, MSS, timeout, pdrop, seed):
        self.addr = (rhost, rport)
        self.MWS = MWS // MSS
        self.MSS = MSS
        self.timeout = timeout * 0.001
        self.pdrop = pdrop
        self.seed = seed
        self.STATE = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        with open(fname, 'rb') as f:
            content = f.read().decode('utf-8')
            self.Amount_of_Original_Data_Transferred = len(content)
            self.container = [[a, content[a:a+self.MSS].encode('utf-8')] for a in range(0, len(content), self.MSS)]     # [seq, data]
        # print(self.container)
        # print([a[1].decode('utf-8') for a in self.container])
        # print()
        self.windows = []
        self.retransmit_seq = -1
        self.init_time = time.time()

        self.send_log = []
        self.receive_log = []

        self.seq = 0
        self.ack = 'x'            # invalid value to indicate it's null
        self.syn = 0
        self.fin = 0

        
        self.Number_of_Data_Segments_Sent = 0
        self.Number_of_All_Packets_Dropped = 0
        self.Number_of_Retransmitted_Segments = 0
        self.Number_of_Duplicate_Ack_Received = 0


    def transfer_cycle(self):
        while self.STATE != 3:
            if self.STATE == 0:
                self.connect()
            elif self.STATE == 1:
                self.transfer()
            elif self.STATE == 2:
                self.disconnect()
            else:
                raise ValueError

        statistic = '\n\nAmount of (original) Data Transferred (in bytes): ' + f'{self.Amount_of_Original_Data_Transferred}\n' + \
                    'Number of Data Segments Sent (excluding retransmissions): ' + f'{self.Number_of_Data_Segments_Sent}\n' + \
                    'Number of (all) Packets Dropped (by the PLD module): ' + f'{self.Number_of_All_Packets_Dropped}\n' + \
                    'Number of Retransmitted Segments: ' + f'{self.Number_of_Retransmitted_Segments}\n' + \
                    'Number of Duplicate Acknowledgements received: ' + f'{self.Number_of_Duplicate_Ack_Received}'

        combine_log = sorted(self.send_log + self.receive_log)
        with open('Sender_log.txt', 'w') as ff:
            ff.write('\n'.join([a[1] for a in combine_log]) + statistic)


    def connect(self):

        # handshake 1
        self.syn = 1
        header = str(self.seq) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|'
        self.socket.sendto(header.encode('utf-8'), self.addr)
        current_time = (time.time() - self.init_time) * 1000
        # print(f'snd\t{current_time:.3f}\t\tS\t{self.seq}\t0\t0')
        self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tS\t{self.seq}\t0\t0'])

        # handshake 2
        packet, server_addr = self.socket.recvfrom(self.MSS + 200)
        self.ack, self.seq, self.syn, self.fin, cont = self.packet_parse(packet)
        current_time = (time.time() - self.init_time) * 1000
        # print(f'rcv\t{current_time:.3f}\t\tSA\t{self.ack}\t0\t{self.seq}')
        self.receive_log.append([current_time, f'rcv\t{current_time:.3f}\t\tSA\t{self.ack}\t0\t{self.seq}'])
        self.ack = int(self.ack) + 1

        # handshake 3
        self.syn = 0
        header = str(self.seq) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|'
        self.socket.sendto(header.encode('utf-8'), self.addr)
        current_time = (time.time() - self.init_time) * 1000
        # print(f'snd\t{current_time:.3f}\t\tA\t{self.seq}\t0\t{self.ack}')
        self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tA\t{self.seq}\t0\t{self.ack}'])

        self.container = [[a[0] + int(self.seq), a[1]] for a in self.container]

        # change state
        self.STATE = 1


    def disconnect(self):
        # print('** in disconnect **', 'self.container:', self.container, '  |||  self.windows:', self.windows, '  |||  self.MWS:', self.MWS)

        # phase 1
        self.fin = 1
        header = str(self.seq) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|'
        self.socket.sendto(header.encode('utf-8'), self.addr)
        current_time = (time.time() - self.init_time) * 1000
        # print(f'snd\t{current_time:.3f}\t\tF\t{self.seq}\t0\t{self.ack}')
        self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tF\t{self.seq}\t0\t{self.ack}'])

        # phase 2
        packet, server_addr = self.socket.recvfrom(self.MSS + 200)
        self.ack, self.seq, self.syn, self.fin, cont = self.packet_parse(packet)
        current_time = (time.time() - self.init_time) * 1000
        # print(f'rcv\t{current_time:.3f}\t\tFA\t{self.ack}\t0\t{self.seq}')
        self.receive_log.append([current_time, f'rcv\t{current_time:.3f}\t\tFA\t{self.ack}\t0\t{self.seq}'])
        self.ack = int(self.ack) + 1

        # phase 3
        self.fin = 0
        header = str(self.seq) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|'
        self.socket.sendto(header.encode('utf-8'), self.addr)
        current_time = (time.time() - self.init_time) * 1000
        # print(f'snd\t{current_time:.3f}\t\tA\t{self.seq}\t0\t{self.ack}')
        self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tA\t{self.seq}\t0\t{self.ack}'])

        self.socket.close()
        self.STATE = 3


    def transfer(self):
        # print('**** DATA TRANSTER ****')
        # print()
        t1 = threading.Thread(target = self.send)
        t2 = threading.Thread(target = self.receive)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        if not (self.container or self.windows):
            self.STATE = 2


    def send(self):

        start_time = [-1, -1]                   # time, seq
        random.seed(self.seed)
        # print('**** THREAD SEND ****')
        # print('len(self.windows):', len(self.windows))
        # print('self.MWS:', self.MWS)
        # print()
        while self.container or self.windows:

            ## regular sending

            if len(self.windows) < self.MWS and self.container:
                
                # print('**********')

                self.Number_of_Data_Segments_Sent += 1

                header = (str(self.container[0][0]) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|').encode('utf-8')

                if random.random() > self.pdrop:
                    self.socket.sendto(header + self.container[0][1], self.addr)
                    current_time = (time.time() - self.init_time) * 1000
                    # print(f'snd\t{current_time:.3f}\t\tD\t{self.container[0][0]}\t{len(self.container[0][1])}\t{self.ack}')
                    self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tD\t{self.container[0][0]}\t{len(self.container[0][1])}\t{self.ack}'])
                    # print('** send packet:', header.decode('utf-8'))
                else:
                    self.Number_of_All_Packets_Dropped += 1
                    # print('** drop packet:', header.decode('utf-8'))
                    current_time = (time.time() - self.init_time) * 1000
                    # print(f'drop\t{current_time:.3f}\t\tD\t{self.container[0][0]}\t{len(self.container[0][1])}\t{self.ack}')
                    self.send_log.append([current_time, f'drop\t{current_time:.3f}\t\tD\t{self.container[0][0]}\t{len(self.container[0][1])}\t{self.ack}'])

                self.windows.append(self.container.pop(0))

            ## timer reset


            # print('start time:', start_time)
            # print('self.windows:', self.windows)

            temp_windows = copy.deepcopy(self.windows)
            if temp_windows and start_time and start_time[1] != temp_windows[0][0]:
                # print('timer reset')
                start_time = [time.time(), temp_windows[0][0]]
                # print('start_time:', start_time)
                # print('self.container:', self.container)
                # print('self.windows:', self.windows)
                # print()

            ## timeout resending

            temp_windows = copy.deepcopy(self.windows)
            if temp_windows and start_time and start_time[1] == temp_windows[0][0] and time.time() - start_time[0] >= self.timeout:
                start_time = [time.time(), temp_windows[0][0]]

                self.Number_of_Retransmitted_Segments += 1

                # print('------------------------------------------------------------------------resending_seq:', temp_windows[0][0])

                header = (str(temp_windows[0][0]) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|').encode('utf-8')

                if random.random() > self.pdrop:
                    self.socket.sendto(header + temp_windows[0][1], self.addr)
                    current_time = (time.time() - self.init_time) * 1000
                    # print(f'snd\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}')
                    self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}'])
                    # print('** resend packet:', header.decode('utf-8'))
                else:
                    self.Number_of_All_Packets_Dropped += 1
                    # print('** redrop packet:', header.decode(:.3f'utf-8'))
                    current_time = (time.time() - self.init_time) * 1000
                    # print(f'drop\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}')
                    self.send_log.append([current_time, f'drop\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}'])

            ## retansmit

            temp_windows = copy.deepcopy(self.windows)

            if self.retransmit_seq > -1 and temp_windows and self.retransmit_seq == temp_windows[0][0]:

                self.Number_of_Retransmitted_Segments += 1

                # print('------------------------------------------------------------------------retransmit_seq:', self.retransmit_seq)
                # print('temp_windows[0][0]:', temp_windows[0][0])

                header = (str(temp_windows[0][0]) + '|' + str(self.ack) + '|' + str(self.syn) + '|' + str(self.fin) + '|').encode('utf-8')

                if random.random() > self.pdrop:
                    self.socket.sendto(header + temp_windows[0][1], self.addr)
                    current_time = (time.time() - self.init_time) * 1000
                    # print(f'snd\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}')
                    self.send_log.append([current_time, f'snd\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}'])
                    # print('** resend packet for retransmit:', header.decode('utf-8'))
                else:
                    self.Number_of_All_Packets_Dropped += 1
                    # print('** redrop packet for retransmit:', header.decode('utf-8'))
                    current_time = (time.time() - self.init_time) * 1000
                    # print(f'drop\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}')
                    self.send_log.append([current_time, f'drop\t{current_time:.3f}\t\tD\t{temp_windows[0][0]}\t{len(temp_windows[0][1])}\t{self.ack}'])

                self.retransmit_seq = -1


    def receive(self):
        # print('**** THREAD RECEIVE ****')
        # print()
        pre_seq = -1
        dup_count = 0
        while self.container or self.windows:
            # print('** in receive loop **', 'self.container:', self.container, '  |||  self.windows:', self.windows, '  |||  self.MWS:', self.MWS)
            # print()
            packet, server_addr = self.socket.recvfrom(self.MSS + 200)
            get_ack, get_seq, get_syn, get_fin, cont = self.packet_parse(packet)
            self.seq = get_seq
            self.ack = get_ack

            current_time = (time.time() - self.init_time) * 1000
            # print(f'rcv\t{current_time:.3f}\t\tA\t{get_ack}\t0\t{get_seq}')
            self.receive_log.append([current_time, f'rcv\t{current_time:.3f}\t\tA\t{get_ack}\t0\t{get_seq}'])

            get_seq = int(get_seq)
            # print('req_seq:', get_seq)
            # print('self.windows:', self.windows)

            if get_seq == pre_seq:
                dup_count += 1
                self.Number_of_Duplicate_Ack_Received += 1
            else:
                dup_count = 1
            if dup_count >= 4:
                self.retransmit_seq = get_seq
                dup_count = 0

            self.windows = [a for a in self.windows if a[0] >= get_seq]
            # print('self.windows*:', self.windows)

            pre_seq = get_seq

    def packet_parse(self, packet):
        data = packet.decode('utf-8').split('|')
        return data[0], data[1], data[2], data[3], '|'.join(data[4:])

# __init__(self, rhost, rport, fname, MWS, MSS, timeout, pdrop, seed)
# sender = sender('', 8888, 'file1.txt', 6000, 500, 20, 1, 50)

sender = sender(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7]), float(sys.argv[8]))
sender.transfer_cycle()