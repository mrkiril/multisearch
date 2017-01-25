import sys
import os
import datetime
import time
import re
import socket
import base64
import json
import mimetypes
import os.path
import logging
import random
import string
import math
import hashlib
import socket
import unittest
from httpclient import HttpClient
import subprocess
import multiprocessing
from time import sleep
import signal


class Test_serv(unittest.TestCase):

    def setUp(self):
        self.file_path = os.path.abspath(os.path.dirname(__file__))
        my_headers = [('User-Agent', 'Mozilla/4.0'), ('X-From', 'UA')]
        my_user_pass = ('kiril', 'supersecret')

        self.client = HttpClient(
            # load cookie from file before query
            load_cookie=os.path.join(self.file_path, 'cookie.txt'),
            # save cookie to file after query
            save_cookie=os.path.join(self.file_path, 'cookie.txt'),
            connect_timeout=10,         # socket timeout on connect
            transfer_timeout=30,        # socket timeout on send/recv
            # follow Location: header on 3xx response
            max_redirects=10,
            # set Referer: header when follow location
            set_referer=True,
            keep_alive=3,               # Keep-alive socket up to N requests
            # headers=my_headers,         # send custom headers
            http_version="1.1",         # use custom http/version
            # auth=my_user_pass,          # http auth
            # try again on socket or http/5xx errors
            retry=5,
            retry_delay=10)             # wait betweet tries

        os.chdir("../")
        self.children = multiprocessing.Value('i', 0)

        p = multiprocessing.Process(target=self.process,
                                    args=(self.children, ),
                                    daemon=False)
        p.start()
        self.pid = p.pid
        print("slave >> " + str(self.pid))
        print("head  >> " + str(os.getpid()))
        print("child >> " + str(self.children.value))

    def process(self, child_pid):
        children = subprocess.Popen(["python3", "search_serv.py"], shell=False)
        child_pid.value = children.pid
        print("OLOLO >> ", child_pid.value)

    def tearDown(self):
        sleep(1)
        print("slave >> " + str(self.pid))
        print("head  >> " + str(os.getpid()))
        print("child >> " + str(self.children.value))

        os.kill(self.pid, signal.SIGINT)
        os.kill(self.children.value, signal.SIGINT)

    def test_page(self):
        sleep(1)
        res = self.client.get('http://127.0.0.1:8080/search?q=tarantino')
        pat1 = re.search("tarantino", res.body)
        # перевірка на успішність запиту
        self.assertEqual(res.status_code, "200")
        # перевірка на наявність слова в видачі
        self.assertIsNotNone(pat1)

        res = self.client.get('http://127.0.0.1:8080/search?q=Рогнар+Лодброк')
        pat1 = re.search("Рогнар", res.body)
        pat2 = re.search("Лодброк", res.body)
        # перевірка на успішність запиту
        self.assertEqual(res.status_code, "200")
        # перевірка на наявність слова в видачі
        self.assertIsNotNone(pat1)
        self.assertIsNotNone(pat2)

        res = self.client.get(
            'http://127.0.0.1:8080/wrong_page.,!@#$%^&*(WTF_page)')
        # перевірка на успішність запиту
        self.assertEqual(res.status_code, "404")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = ("127.0.0.1", 8080)
        sock.connect(addr)
        CRLF = b"\r\n"
        q = b"GETT /search?q=tarantino HTTP/1.1" + CRLF
        q += b"User-Agent: Mozilla/4.0 (compatible; MSIE5.01; Windows NT)" + \
            CRLF
        q += b"Host: 127.0.0.1:8080" + CRLF
        q += b"Connection: Close" + CRLF
        q += CRLF
        sock.send(q)
        response = b""
        response += sock.recv(65535)
        status = re.search(b"HTTP.*? (\d+) ", response[:16])
        status_code = status.group(1).decode()
        self.assertEqual(status_code, "400")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = ("127.0.0.1", 8080)
        sock.connect(addr)
        CRLF = b"\r\n"
        q = b"/GET /search?q=tarantino HTTP/1.1" + CRLF
        q += b"User-Agent: Mozilla/4.0 (compatible; MSIE5.01; Windows NT)" + \
            CRLF
        q += b"Host: 127.0.0.1:8080" + CRLF
        q += b"Connection: Close" + CRLF
        q += CRLF
        sock.send(q)
        response = b""
        response += sock.recv(65535)
        status = re.search(b"HTTP.*? (\d+) ", response[:16])
        status_code = status.group(1).decode()
        self.assertEqual(status_code, "400")


if __name__ == '__main__':
    unittest.main()
