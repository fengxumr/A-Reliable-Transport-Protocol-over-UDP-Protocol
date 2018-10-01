import socket
import sys
import time

class receiver(object):
    def __init__(self, port, fname):
        self.port = port
        self.fname = fname
        self.content = []
        self.Amount_of_Original_Data_Received = 0
        self.Number_of_Original_Data_Segments_Received = 0
        self.Number_of_Duplicate_Segments_Received = 0
        self.log = []
        self.init_time = 0


    def receive(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', self.port))

        init_ack = 1000
        pre_syn = 'x'
        acc_ack_got = []
        acc_ack_req = []

        while True:
            packet, client_addr = self.socket.recvfrom(2048)
            if self.init_time == 0:
                self.init_time = time.time()
            get_seq, get_ack, get_syn, get_fin, cont = self.packet_parse(packet)
            # print('get_seq:', get_seq)
            # print('get_ack:', get_ack)
            # print('get_syn:', get_syn)
            # print('pre_syn:', pre_syn)
            # print()

            current_time = (time.time() - self.init_time) * 1000
            if get_syn == '1':
                sign = 'S'
                get_ack = init_ack
            elif get_fin == '1':
                sign = 'F'
            elif cont == '':
                sign = 'A'
            elif cont != '':
                sign = 'D'
            else:
                raise ValueError
            self.log.append(f'rcv\t{current_time:.3f}\t\t{sign}\t{get_seq}\t{len(cont)}\t{get_ack}')


            if get_syn == '1':
                get_ack = init_ack
                get_seq = int(get_seq) + 1
            elif get_syn == '0' and pre_syn == '1':
                # print('*********')
                # print()
                get_seq = int(get_seq)
                acc_ack_req.append(get_seq)
                pre_syn = get_syn
                continue
            elif get_fin == '1':
                get_seq = int(get_seq) + 1
            elif get_fin == '0' and pre_fin == '1':
                break
            else:
                # if int(get_seq) in acc_ack_req:
                #     print(get_seq)
                #     print(acc_ack_req)
                #     acc_ack_req.pop(acc_ack_req.index(int(get_seq)))

                get_seq = int(get_seq)
                self.content.append((get_seq, cont))
                acc_ack_got.append(get_seq)
                get_seq += len(cont)
                acc_ack_req.append(get_seq)

                get_seq = sorted(list(set(acc_ack_req) - set(acc_ack_got)))[0]
                # print('acc_ack_got:', acc_ack_got)
                # print('acc_ack_req:', acc_ack_req)
                # print('diff:', sorted(list(set(acc_ack_req) - set(acc_ack_got))))

            ####################

            pre_syn = get_syn
            pre_fin = get_fin

            header = (str(get_ack) + '|' + str(get_seq) + '|' + str(get_syn) + '|' + str(get_fin) + '|').encode('utf-8')
            self.socket.sendto(header, client_addr)

            current_time = (time.time() - self.init_time) * 1000

            if get_syn == '1':
                sign = 'SA'
            elif get_fin == '1':
                sign = 'FA'
            elif get_syn == '0':
                sign = 'A'
            else:
                raise ValueError
            self.log.append(f'snd\t{current_time:.3f}\t\t{sign}\t{get_ack}\t{len(cont)}\t{get_seq}')

            # print(repr(packet.decode('utf-8')))
            # print(repr(header.decode('utf-8')))
            # print()

        with open(self.fname, 'w') as f:
            f.write(''.join([a[1] for a in sorted(list(set(self.content)))]))

        content_list_len = len(self.content)
        content_set_len = len(set(self.content))

        self.Amount_of_Original_Data_Received = sum([len(a[1]) for a in list(set(self.content))])
        self.Number_of_Original_Data_Segments_Received = content_set_len
        self.Number_of_Duplicate_Segments_Received = content_list_len - content_set_len

        statistic = '\n\nAmount of (original) Data Received (in bytes): ' + f'{self.Amount_of_Original_Data_Received}\n' + \
                    'Number of (original) Data Segments Received: ' + f'{self.Number_of_Original_Data_Segments_Received}\n' + \
                    'Number of duplicate segments received: ' + f'{self.Number_of_Duplicate_Segments_Received}\n'

        with open('Receiver_log.txt', 'w') as ff:
            ff.write('\n'.join(self.log) + statistic)

    def packet_parse(self, packet):
        data = packet.decode('utf-8').split('|')
        return data[0], data[1], data[2], data[3], '|'.join(data[4:])

# receiver = receiver(8888, 'file_out.txt')

receiver = receiver(int(sys.argv[1]), sys.argv[2])
receiver.receive()