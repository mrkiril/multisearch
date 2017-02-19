#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import re
import socket
import unittest
from httpclient import HttpClient
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
        sleep(1)
        print("slave >> " + str(self.pid))
        print("head  >> " + str(os.getpid()))
        print("child >> " + str(self.children.value))

        os.kill(self.children.value, signal.SIGINT)
        print("IS_ALIVE >> ", self.p.is_alive())
        self.p.terminate()

        try:
            os.kill(self.children.value, signal.SIGINT)
        except Exception as e:
            print("try to kill child", self.children.value, " but Exception")
            print(e.args)
        try:
            os.kill(self.pid, signal.SIGINT)
        except Exception as e:
            print("try to kill ", self.pid, " but Exception")
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
        self.assertRegex(res.body, "Ragnar")
        self.assertRegex(res.body, "Lodbrok")
        self.assertEqual(res.status_code, "200")
        # перевірка на наявність слова в видачі
        

        res = self.client.get(
            'http://' + self.sock + '/wrong_page.,!@#$%^&*(WTF_page)')
        self.assertEqual(res.status_code, "404")

        res = self.client.get('http://' + self.sock + '/test_timeout')
        self.assertEqual(res.status_code, "")

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
        q = b"/GET /search?q=tarantino HTTP/1.1" + CRLF
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


if __name__ == '__main__':
    unittest.main()
