#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import re
import socket
import unittest
from httpclient import HttpClient
from httpserver import BaseServer
import subprocess
import multiprocessing
from time import sleep
import signal
import configparser
import logging
import logging.config


class Test_serv(unittest.TestCase):

    def setUp(self):
        logging.config.fileConfig(
            os.path.join(os.getcwd(), "logging.conf"))
        self.file_path = os.path.abspath(os.path.dirname(__file__))
        my_headers = [('User-Agent', 'Mozilla/4.0'), ('X-From', 'UA')]
        my_user_pass = ('kiril', 'supersecret')

        self.client = HttpClient(
            connect_timeout=10,         # socket timeout on connect
            transfer_timeout=5,        # socket timeout on send/recv
            max_redirects=10,
            set_referer=True,
            keep_alive=3,               # Keep-alive socket up to N requests
            http_version="1.1",         # use custom http/version
            retry=5,
            retry_delay=10)             # wait betweet tries

        self.client.logger = logging.getLogger("httpclient_test")
        os.chdir("../")
        self.children = multiprocessing.Value('i', 0)

        self.p = multiprocessing.Process(target=self.process,
                                         args=(self.children, ),
                                         daemon=False)
        self.p.start()
        self.pid = self.p.pid
        print("slave >> " + str(self.pid))
        print("head  >> " + str(os.getpid()))
        print("child >> " + str(self.children.value))
        config = configparser.ConfigParser()
        config.read(os.path.join(self.file_path,
                                 "..", "setting", "setting.ini"))
        print(os.path.join(self.file_path, "..", "setting", "setting.ini"))
        self.ip = config['DEFAULT']["ip"]
        self.port = config['DEFAULT']["port"]
        self.sock = self.ip + ":" + self.port

    def process(self, child_pid):
        children = subprocess.Popen(["python3", "search_serv.py"], shell=False)
        child_pid.value = children.pid
        print("OLOLO >> ", child_pid.value)

    def tearDown(self):
        sleep(2)
        print("slave >> " + str(self.pid))
        print("head  >> " + str(os.getpid()))
        print("child >> " + str(self.children.value))
        os.kill(self.children.value, signal.SIGINT)
        print("IS_ALIVE >> ", self.p.is_alive())
        sleep(1)
        try:
           os.kill(self.children.value, signal.SIGINT)
        except Exception as e:
           print("try to kill child", self.children.value, " but Exception")
           print(e.args)


    def test_page(self):
        sleep(1)
        res = self.client.get('http://' + self.sock + '/search?q=tarantino',
                              retry=1)
        self.assertEqual(res.status_code, "200")

        res = self.client.get('http://' + self.sock + '/search'
                              '?q=ragnar+lothbrok',
                              output=os.path.join(self.file_path,
                                                  "socket_page.html"))
        self.assertRegex(res.body, b"Ragnar")
        self.assertEqual(res.status_code, "200")
        # перевірка на наявність слова в видачі

        res = self.client.get('http://' + self.sock + '/search',
                              params={"q": "Uma Turman"},
                              output=os.path.join(self.file_path,
                                                  "socket_page.html"))
        self.assertRegex(res.body, b"Uma")
        self.assertEqual(res.status_code, "200")
        # перевірка на наявність слова в видачі

        res = self.client.get(
            'http://' + self.sock + '/wrong_page.,!@#$%^&*(WTF_page)')
        self.assertEqual(res.status_code, "404")

        res = self.client.post('http://' + self.sock + '/search',
                               data={'k1': 'value', 'k2': 'eulav'})
        self.assertEqual(res.status_code, "415")

        

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = (self.ip, int(self.port))
        sock.connect(addr)
        CRLF = b"\r\n"
        q = b"GETT /search?q=tarantino HTTP/1.1" + CRLF
        q += b"User-Agent: Mozilla/4.0 (compatible; MSIE5.01; Windows NT)" + \
            CRLF
        q += b"Host: " + self.sock.encode() + CRLF
        q += b"Connection: Close" + CRLF
        q += CRLF
        sock.send(q)
        response = b""
        response += sock.recv(65535)
        status = re.search(b"HTTP.*? (\d+) ", response[:16])
        status_code = status.group(1).decode()
        self.assertEqual(status_code, "400")
        sock.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = (self.ip, int(self.port))
        sock.connect(addr)
        CRLF = b"\r\n"
        q = b"\r\n\r\nGET /search?q=tarantino HTTP/1.1" + CRLF
        q += b"User-Agent: Mozilla/4.0 (compatible; MSIE5.01; Windows NT)" + \
            CRLF
        q += b"Host: " + self.sock.encode() + CRLF
        q += b"Connection: Close" + CRLF
        q += CRLF

        sock.send(q)
        response = sock.recv(65535)
        sock.close()
        status = re.search(b"HTTP.*? (\d+) ", response[:16])
        status_code = status.group(1).decode()
        start, end = re.search(b"\r\n\r\n", response).span()
        self.assertEqual(status_code, "200")


if __name__ == '__main__':
    unittest.main()
