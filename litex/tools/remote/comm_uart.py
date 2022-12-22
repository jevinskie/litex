#
# This file is part of LiteX.
#
# Copyright (c) 2015-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2022      Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import select
import socket

import serial

from litex.tools.remote.csr_builder import CSRBuilder

# Constants ----------------------------------------------------------------------------------------

CMD_WRITE_BURST_INCR  = 0x01
CMD_READ_BURST_INCR   = 0x02
CMD_WRITE_BURST_FIXED = 0x03
CMD_READ_BURST_FIXED  = 0x04

# CommUART -----------------------------------------------------------------------------------------

class CommUART(CSRBuilder):
    def __init__(self, port, baudrate=115200, csr_csv=None, debug=False):
        CSRBuilder.__init__(self, comm=self, csr_csv=csr_csv)
        self.port     = serial.serial_for_url(port, baudrate)
        self.baudrate = str(baudrate)
        self.debug    = debug

    def open(self):
        if hasattr(self, "port"):
            return
        self.port.open()

    def close(self):
        if not hasattr(self, "port"):
            return
        self.port.close()
        del self.port

    def _read(self, length):
        r = bytes()
        while len(r) < length:
            r += self.port.read(length - len(r))
        return r

    def _write(self, data):
        remaining = len(data)
        pos = 0
        while remaining:
            written = self.port.write(data[pos:])
            remaining -= written
            pos += written

    def _flush(self):
        if self.port.inWaiting() > 0:
            self.port.read(self.port.inWaiting())

    def read(self, addr, length=None, burst="incr"):
        self._flush()
        data       = []
        length_int = 1 if length is None else length
        cmd        = {
            "incr" : CMD_READ_BURST_INCR,
            "fixed": CMD_READ_BURST_FIXED,
        }[burst]
        self._write([cmd, length_int])
        self._write(list((addr//4).to_bytes(4, byteorder="big")))
        for i in range(length_int):
            value = int.from_bytes(self._read(4), "big")
            if self.debug:
                print("read 0x{:08x} @ 0x{:08x}".format(value, addr + 4*i))
            if length is None:
                return value
            data.append(value)
        return data

    def write(self, addr, data, burst="incr"):
        self._flush()
        data   = data if isinstance(data, list) else [data]
        length = len(data)
        offset = 0
        while length:
            size = min(length, 8)
            cmd = {
                "incr" : CMD_WRITE_BURST_INCR,
                "fixed": CMD_WRITE_BURST_FIXED,
            }[burst]
            self._write([cmd, size])
            self._write(list(((addr//4 + offset).to_bytes(4, byteorder="big"))))
            for i, value in enumerate(data[offset:offset+size]):
                self._write(list(value.to_bytes(4, byteorder="big")))
                if self.debug:
                    print("write 0x{:08x} @ 0x{:08x}".format(value, addr + offset, 4*i))
            offset += size
            length -= size

# CommUARTTCP --------------------------------------------------------------------------------------

class CommUARTTCP(CommUART):
    def __init__(self, hostname, port, csr_csv=None, debug=False):
        CSRBuilder.__init__(self, comm=self, csr_csv=csr_csv)
        self.hostname = hostname
        self.port     = port
        self.debug    = debug

    def open(self):
        if self.debug:
            print(f"open {self.hostname}:{self.port}")
        if hasattr(self, "socket"):
            return
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, self.port))


    def close(self):
        if self.debug:
            print(f"close")
        if not hasattr(self, "socket"):
            return
        self.socket.close()
        del self.socket

    def _read(self, length):
        if self.debug:
            print(f"_read {length}")
        r = bytes()
        while len(r) < length:
            select.select([self.socket], [], [])
            rbuf = self.socket.recv(length - len(r))
            if rbuf == b"":
                self.close()
                self.open()
                r = bytes()
            if self.debug:
                print(f"_read recv {len(rbuf)}")
            r += rbuf
        return r

    def _write(self, data):
        if self.debug:
            print(f"_write {len(data)}")
        remaining = len(data)
        pos = 0
        while remaining:
            rd_bufs, wr_bufs, _ = select.select([self.socket], [self.socket], [])
            if len(rd_bufs):
                rbuf = self.socket.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
                if not len(rbuf):
                    self.close()
                    self.open()
                    remaining = len(data)
                    pos = 0
                    continue
            if not len(wr_bufs):
                continue
            written = self.socket.send(bytes(data[pos:]))
            if self.debug:
                print(f"_write send {written}")
            remaining -= written
            pos += written

    def _flush(self):
        return
