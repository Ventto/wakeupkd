#!/usr/bin/env python
#
# MIT License
#
# Copyright (c) 2016 Thomas "Ventto" Venriès
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import ipaddress
import os
import signal
import socket
import struct
import sys

WOLH_PASSWD_NONE     = 102
DEFAULT_PORT         = 9
HOST                 = socket.gethostbyname(socket.getfqdn())

# Check on MAC address validity in WOL packet data
def __wol_datacheck(macaddr, data):
    mac_bytes = bytearray.fromhex(macaddr.replace(':', ''))
    for i in range(6):
        if data[i] != 0xFF:
            return False
    j = 0
    for i in range(6, 102):
        if data[i] != mac_bytes[j]:
            return False
        j = (j + 1) % 6
    return True

# Check on WOL packet validity
def __wol_pktcheck(packet, macaddr, ipsrc=None, port=None):
    iph         = struct.unpack('!BBHHHBBHL4s' , packet[0:20])
    iph_version = iph[0] >> 4
    iph_len     = (iph[0] & 0xF) * 4
    iph_ipsrc   = iph[8]

    if ipsrc != None and int(ipaddress.IPv4Address(ipsrc)) != iph_ipsrc:
        return False

    udph        = struct.unpack('!4H' , packet[iph_len: iph_len + 8])
    udph_len    = udph[2];
    udph_port   = udph[1];

    if udph_port != port:
        return False

    wolh_off    = iph_len + 8
    wolh_len    = udph_len - 8

    if wolh_len == WOLH_PASSWD_NONE:
        wolh = struct.unpack('!102B', packet[wolh_off:wolh_off + wolh_len])
        if macaddr != None and not __wol_datacheck(macaddr, wolh):
            return False
        return True
    return False

def __handle_sigs_for(socket):
    def on_exit(signal, frame):
        socket.close()
        sys.exit()
    signal.signal(signal.SIGTERM, on_exit)
    signal.signal(signal.SIGINT, on_exit)

def __getopt():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest='cmd', help="Shell CMD to execute [required]",
            required=True)
    parser.add_argument('-m', dest='macaddr',
            help="Identifies wol packets with a destination MACADDR [required]",
            required=True)
    parser.add_argument('-i', dest='ipsrc',
            help="Specifies an IPSRC address")
    parser.add_argument('-p', dest='port',
            help="Specifies a port NUM, (default=9)")
    return parser.parse_args()

def main():
    args = __getopt()
    args.port = DEFAULT_PORT if args.port == None else int(args.port)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        sock.bind((HOST, args.port))
    except socket.error as msg:
        print ('Cannot create socket. Error: ' + str(msg[0]) + ') Message:' + str(msg[1]))
        sys.exit()

    __handle_sigs_for(sock)

    wol_found = False
    while True:
        packet = sock.recv(65565)

        if (__wol_pktcheck(packet, args.macaddr, args.ipsrc, args.port)
                and not wol_found):
            print("Kore: <WakeUp>")
            os.system(args.cmd)
            wol_found = True
        else:
            wol_found = False

if __name__ == "__main__":
    main()
