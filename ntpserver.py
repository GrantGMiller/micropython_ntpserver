import socket
import ustruct as struct
import time
import select
import network as net
from ucollections import deque
from machine import RTC

stopFlag = False
taskQueue = deque((), 10)
rtc = RTC()


def system_to_ntp_time(timestamp):
    # #"""Convert a system time to a NTP time.
    # 
    # Parameters:
    # timestamp -- timestamp in system time
    # 
    # Returns:
    # corresponding NTP time
    # #"""
    espOffset = 940784212  # diff between normal time.gmtime() (on windows for example) and esp time.time() (assuming the rtc is set)
    return timestamp + NTP.NTP_DELTA + espOffset  #


def _to_int(timestamp):
    # #"""Return the integral part of a timestamp.
    # 
    # Parameters:
    # timestamp -- NTP timestamp
    # 
    # Retuns:
    # integral part
    # #"""
    return int(timestamp)


def _to_frac(timestamp, n=32):
    # #"""Return the fractional part of a timestamp.
    # 
    # Parameters:
    # timestamp -- NTP timestamp
    # n         -- number of bits of the fractional part
    # 
    # Retuns:
    # fractional part
    # #"""
    return int(abs(timestamp - _to_int(timestamp)) * 2 ** n)


def _to_time(integ, frac, n=32):
    # #"""Return a timestamp from an integral and fractional part.
    # 
    # Parameters:
    # integ -- integral part
    # frac  -- fractional part
    # n     -- number of bits of the fractional part
    # 
    # Retuns:
    # timestamp
    # #"""
    return integ + float(frac) / 2 ** n


class NTPException(Exception):
    # """Exception raised by this module.#"""
    pass


class NTP:
    # """Helper class defining constants.#"""

    # """NTP epoch#"""
    # NTP_DELTA = 2208988800# original
    NTP_DELTA = 2208988800
    # """delta between system and NTP time#"""

    REF_ID_TABLE = {
        'DNC': "DNC routing protocol",
        'NIST': "NIST public modem",
        'TSP': "TSP time protocol",
        'DTS': "Digital Time Service",
        'ATOM': "Atomic clock (calibrated)",
        'VLF': "VLF radio (OMEGA, etc)",
        'callsign': "Generic radio",
        'LORC': "LORAN-C radionavidation",
        'GOES': "GOES UHF environment satellite",
        'GPS': "GPS UHF satellite positioning",
    }
    # """reference identifier table#"""

    STRATUM_TABLE = {
        0: "unspecified",
        1: "primary reference",
    }
    # """stratum table#"""

    MODE_TABLE = {
        0: "unspecified",
        1: "symmetric active",
        2: "symmetric passive",
        3: "client",
        4: "server",
        5: "broadcast",
        6: "reserved for NTP control messages",
        7: "reserved for private use",
    }
    # """mode table#"""

    LEAP_TABLE = {
        0: "no warning",
        1: "last minute has 61 seconds",
        2: "last minute has 59 seconds",
        3: "alarm condition (clock not synchronized)",
    }
    # """leap indicator table#"""


class NTPPacket:
    # """NTP packet class.

    # This represents an NTP packet.
    # #"""
    #
    # _PACKET_FORMAT = "!B B B b 11I" # original
    _PACKET_FORMAT = "!BBBb11I"

    # """packet format to pack/unpack#"""

    def __init__(self, version=2, mode=3, tx_timestamp=0):
        print('__init__', version, mode, tx_timestamp)
        # """Constructor.

        # Parameters:
        # version      -- NTP version
        # mode         -- packet mode (client, server)
        # tx_timestamp -- packet transmit timestamp
        # """
        self.leap = 0
        # """leap second indicator#"""
        self.version = version
        # """version#"""
        self.mode = mode
        # """mode#"""
        self.stratum = 0
        # """stratum#"""
        self.poll = 0
        # """poll interval#"""
        self.precision = 0
        # """precision#"""
        self.root_delay = 0
        # """root delay#"""
        self.root_dispersion = 0
        # """root dispersion#"""
        self.ref_id = 0
        # """reference clock identifier#"""
        self.ref_timestamp = 0
        # """reference timestamp#"""
        self.orig_timestamp = 0
        self.orig_timestamp_high = 0
        self.orig_timestamp_low = 0
        # """originate timestamp#"""
        self.recv_timestamp = 0
        # """receive timestamp#"""
        self.tx_timestamp = tx_timestamp
        self.tx_timestamp_high = 0
        self.tx_timestamp_low = 0
        # """tansmit timestamp#"""

    def to_data(self):
        # """Convert this NTPPacket to a buffer that can be sent over a thisSocket.

        # Returns:
        # buffer representing this packet
        #
        # Raises:
        # NTPException -- in case of invalid field
        # """
        print('to_data')
        try:
            packed = struct.pack(
                NTPPacket._PACKET_FORMAT,
                (self.leap << 6 | self.version << 3 | self.mode),
                self.stratum,
                self.poll,
                self.precision,
                _to_int(self.root_delay) << 16 | _to_frac(self.root_delay, 16),
                _to_int(self.root_dispersion) << 16 |
                _to_frac(self.root_dispersion, 16),
                self.ref_id,
                _to_int(self.ref_timestamp),
                _to_frac(self.ref_timestamp),
                # Change by lichen, avoid loss of precision
                self.orig_timestamp_high,
                self.orig_timestamp_low,
                _to_int(self.recv_timestamp),
                _to_frac(self.recv_timestamp),
                _to_int(self.tx_timestamp),
                _to_frac(self.tx_timestamp)
            )
        except Exception as e196:
            raise NTPException("203 Invalid NTP packet fields." + str(e196))
        return packed

    def from_data(self, data):
        print('from_data(', data)
        # """Populate this instance from a NTP packet payload received from
        # the network.

        # Parameters:
        # data -- buffer payload

        # Raises:
        # NTPException -- in case of invalid packet format
        # """
        try:
            csize = struct.calcsize(NTPPacket._PACKET_FORMAT)
            print('csize=', csize)
            print('len(data)=', len(data))
            unpacked = struct.unpack(
                NTPPacket._PACKET_FORMAT,
                data[0:csize]
            )
        except Exception as e213:
            raise NTPException("220 Invalid NTP packet. " + str(e213))

        self.leap = unpacked[0] >> 6 & 0x3
        self.version = unpacked[0] >> 3 & 0x7
        self.mode = unpacked[0] & 0x7
        self.stratum = unpacked[1]
        self.poll = unpacked[2]
        self.precision = unpacked[3]
        self.root_delay = float(unpacked[4]) / 2 ** 16
        self.root_dispersion = float(unpacked[5]) / 2 ** 16
        self.ref_id = unpacked[6]
        self.ref_timestamp = _to_time(unpacked[7], unpacked[8])
        self.orig_timestamp = _to_time(unpacked[9], unpacked[10])
        self.orig_timestamp_high = unpacked[9]
        self.orig_timestamp_low = unpacked[10]
        self.recv_timestamp = _to_time(unpacked[11], unpacked[12])
        self.tx_timestamp = _to_time(unpacked[13], unpacked[14])
        self.tx_timestamp_high = unpacked[13]
        self.tx_timestamp_low = unpacked[14]

    def GetTxTimeStamp(self):
        print('GetTxTimeStamp()')
        print('tx_timestamp_high=', self.tx_timestamp_high)
        print('tx_timestamp_low=', self.tx_timestamp_low)
        return self.tx_timestamp_high, self.tx_timestamp_low

    def SetOriginTimeStamp(self, high, low):
        print('SetOriginTimeStamp(', high, low)
        self.orig_timestamp_high = high
        self.orig_timestamp_low = low


class RecvThread:
    def __init__(self, socket):
        self.socket = socket

    def DoWork(self):
        global taskQueue, stopFlag
        # print('RecvThread.DoWork() taskQueue=', taskQueue)
        rlist, wlist, elist = select.select([self.socket], [], [], 1)
        if len(rlist) != 0:
            print("Received %d packets" % len(rlist))
            for tempSocket in rlist:
                try:
                    data, addr = tempSocket.recvfrom(1024)
                    recvTimestamp = system_to_ntp_time(time.time())
                    taskQueue.append((data, addr, recvTimestamp))
                except Exception as e272:
                    print('263 Exception:', e272)


class WorkThread:
    def __init__(self, socket):
        self.socket = socket

    def DoWork(self):
        global taskQueue, stopFlag
        # print('WorkThread.DoWork() taskQueue=', taskQueue)
        try:
            data, addr, recvTimestamp = taskQueue.popleft()
            recvPacket = NTPPacket()
            recvPacket.from_data(data)
            timeStamp_high, timeStamp_low = recvPacket.GetTxTimeStamp()
            sendPacket = NTPPacket(version=3, mode=4)
            sendPacket.stratum = 2
            sendPacket.poll = 10
            '''
            sendPacket.precision = 0xfa
            sendPacket.root_delay = 0x0bfa
            sendPacket.root_dispersion = 0x0aa7
            sendPacket.ref_id = 0x808a8c2c
            '''
            sendPacket.ref_timestamp = recvTimestamp - 5
            sendPacket.SetOriginTimeStamp(timeStamp_high, timeStamp_low)
            sendPacket.recv_timestamp = recvTimestamp
            sendPacket.tx_timestamp = system_to_ntp_time(time.time())
            thisSocket.sendto(sendPacket.to_data(), addr)
            print("Sended to %s:%d" % (addr[0], addr[1]))
        except Exception as e:
            print('290 Exception:', e)


listenIp = "0.0.0.0"
listenPort = 123  # should be 123
thisSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
thisSocket.bind((listenIp, listenPort))
print("local thisSocket: ", thisSocket)
recvThread = RecvThread(thisSocket)
workThread = WorkThread(thisSocket)

print('starting ntpserver')
while True:
    recvThread.DoWork()
    workThread.DoWork()
    print('IP:', net.WLAN(net.STA_IF).ifconfig()[0])
    print('RTC:', rtc.datetime())
