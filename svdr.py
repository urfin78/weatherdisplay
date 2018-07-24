#!/usr/bin/env python3
# class for communication with vdr

from collections import namedtuple
from datetime import datetime, timedelta
import socket
import re


class svdr():
    def __init__(self, host, port, timeout):
        self.channels = {
                '2': 'zdf.bmp',
                '7': 'pro7.bmp',
                '32': 'zdfneo.bmp'
                }
        self.CRLF = '\r\n'
        self.raw = namedtuple('Response', 'code delim text')
        self.socket = socket.create_connection((host, port), timeout)
        self.sfile = self.socket.makefile('r')
        self.conpattern = r'^(\d+)(\s|-)(.+)$'
        self.response_regex = re.compile(self.conpattern, flags=re.U)
        self.response = []
        self.next_index = len(self.response)
        for rline in self.sfile:
            self.message = self.response_regex.search(rline)
            self.part = self.raw(int(self.message.group(1)), self.message.group(2), self.message.group(3))
            self.response.append(self.part)
            if self.part.delim != '-':
                break

    def close_connection(self):
        self.sfile.close()
        self.socket.close()
        self.sfile = self.socket = None

    def send(self, cmd):
        self.cparts = []
        self.cparts.append(cmd)
        self.cparts.append(self.CRLF)
        self.command = ''
        self.command = self.command.join(self.cparts)
        self.socket.send(self.command.encode('utf-8'))
        return self.get_response()

    def get_response(self):
        self.raw = namedtuple('Response', ['code', 'delim', 'id', 'chan', 'date', 'start', 'end', 'text'])
        self.lsttpattern = r'^(\d+)(\s|-)(\d+)(?:\s\d+:)(\d+)(?::)(\d{4}-[0-1]\d-[0-3]\d)(?::)(\d{4})(?::)(\d{4})(?:(?::\d+){2}:)([^~:]+)(?:.*)$'
        self.response_regex = re.compile(self.lsttpattern, re.U)
        self.next_index = len(self.response)
        for rline in self.sfile:
            self.message = self.response_regex.search(rline)
            self.part = self.raw(int(self.message.group(1)), self.message.group(2), self.message.group(3), self.message.group(4), self.message.group(5), self.message.group(6), self.message.group(7),  self.message.group(8))
            self.response.append(self.part)
            if self.part.delim != '-':
                break
        self.timerlist = self.response[self.next_index:]

    def get_next_timer(self):
        self.timer = namedtuple('Timer',['channel', 'date', 'start', 'end', 'text'])
        self.ttime = self.timerlist[0].date + " " + self.timerlist[0].start
        self.ttime = datetime.strptime(self.ttime, "%Y-%m-%d %H%M")
        self.ntimestart = datetime.now() + timedelta(days=999)
        for i in range(0, len(self.timerlist)):
            self.ttime = self.timerlist[i].date + " " + self.timerlist[i].start
            self.ttime = datetime.strptime(self.ttime, "%Y-%m-%d %H%M")
            if self.ttime < self.ntimestart:
                self.ntimestart = self.ttime
                if self.timerlist[i].start > self.timerlist[i].end:
                    self.ntimeend = self.timerlist[i].date + " " + self.timerlist[i].end
                    self.ntimeend = datetime.strptime(self.ntimeend, "%Y-%m-%d %H%M") + timedelta(days=1)
                else:
                    self.ntimeend = self.timerlist[i].date + " " + self.timerlist[i].end
                    self.ntimeend = datetime.strptime(self.ntimeend, "%Y-%m-%d %H%M")
                self.tid = i
        if self.timerlist[self.tid].chan in self.channels:
            self.nexttimer = self.timer(self.channels[self.timerlist[self.tid].chan], self.timerlist[self.tid].date, self.ntimestart, self.ntimeend, self.timerlist[self.tid].text)
        else:
            self.nexttimer = self.timer('unbekannt.bmp', self.timerlist[self.tid].date, self.ntimestart, self.ntimeend, self.timerlist[self.tid].text)
