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
        self.ip = config['ip_port_setting']["ip"]
        self.port = config['ip_port_setting']["port"]
        self.sock = self.ip + ":" + self.port

    def process(self, child_pid):
        children = subprocess.Popen(["python3", "search_serv.py"], shell=False)
        child_pid.value = children.pid

    def tearDown(self):
        sleep(1)
        print("slave >> " + str(self.pid))
        print("head  >> " + str(os.getpid()))
        print("child >> " + str(self.children.value))
        os.kill(self.children.value, signal.SIGINT)
        print("IS_ALIVE >> ", self.p.is_alive())

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
                              params={"q": "Olimp"},
                              output=os.path.join(self.file_path,
                                                  "socket_page.html"))
        self.assertRegex(res.body, b"olimp")
        self.assertEqual(res.status_code, "200")
        # перевірка на наявність слова в видачі

        res = self.client.get(
            'http://' + self.sock + '/wrong_page.,!@#$%^&*(WTF_page)')
        self.assertEqual(res.status_code, "404")

        res = self.client.post('http://' + self.sock + '/search',
                               data={'k1': 'value', 'k2': 'eulav'})
        self.assertEqual(res.status_code, "415")

        # GETT неіснуючий запит
        #
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = (self.ip, int(self.port))
        sock.connect(addr)
        CRLF = b"\r\n"
        q = b"GETT /search?q=tarantino HTTP/1.1" + CRLF
        q += b"User-Agent: Mozilla/4.0" + CRLF
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

        # CRLF перед запитом
        # погані хедери
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr = (self.ip, int(self.port))
        sock.connect(addr)
        CRLF = b"\r\n"
        q = b"\r\n\r\nGET /search?q=dino HTTP/1.1" + CRLF
        q += b"User-Agent: Mozilla/4.0" + CRLF
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

        # криві кукі від сервера
        # невірний контент лен
        # замість хтмл картинка
        # а якщо прийде в UTF16 і не буде вказане кодування?
        # прийде в 1251 а буде вказано utf-8 в заголовках та 1251 в тексті HTML
        # ?

        # data len is less that Content len num
        #
        #
        CRLF = "\r\n"
        q = ""
        q += "HTTP/1.1 200 OK" + CRLF
        q += "Connection: close" + CRLF
        q += "Content-Length: 5" + CRLF
        q += "Content-Type: text/html" + CRLF
        q += CRLF
        q += "w"
        res = self.client.post('http://' + self.sock + '/test',
                               data={"hed": q})
        self.assertEqual(res.body, b"")

        # data more that content len num
        #
        #
        CRLF = "\r\n"
        q = ""
        q += "HTTP/1.1 200 OK" + CRLF
        q += "Connection: close" + CRLF
        q += "Content-Length: 5" + CRLF
        q += "Content-Type: text/html" + CRLF
        q += CRLF
        q += "LALKA LALKA" * 10000
        res = self.client.post('http://' + self.sock + '/test',
                               data={"hed": q})
        self.assertEqual(res.body, b"LALKA")

        # Broke COOKIES
        # cookies did not append to cookies dictionary
        #
        CRLF = "\r\n"
        q = ""
        q += "HTTP/1.1 200 OK" + CRLF
        q += "Connection: close" + CRLF
        q += "Content-Length: 5" + CRLF
        q += "Content-Type: text/html; charset=utf-8" + CRLF
        q += "Set-Cookie: k=v; "
        q += "expires=ww*, 09-***-2019 23:12:40 GMT; path=/" + CRLF
        q += CRLF
        q += "LOLKO LOLKO"
        res = self.client.post('http://' + self.sock + '/test',
                               data={"hed": q})
        self.assertEqual(res.body, b"LOLKO")
        self.assertEqual(res.cook_dick, {})

        # wrong_encoding
        # body encode cp1251
        # in headers utf-8
        res = self.client.get('http://' + self.sock + '/wrong_encoding')
        self.assertEqual(res.body.decode("cp1251"), "ЛЯЛЯЛЯ ЛЯЛЯЛЯ")
        print(res.body)


if __name__ == '__main__':
    unittest.main()
