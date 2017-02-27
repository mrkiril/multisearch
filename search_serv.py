#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import os
import sys
import re
import socket
import logging
import logging.config
import configparser
from search_resp import main_import
from search_resp import SETTINGS
from search_resp import client
from httpserver import BaseServer
from httpserver import HttpResponse
from httpserver import HttpErrors
from time import sleep


class MyServer(BaseServer):

    """ Class of a base class that implements
        configure method of the list of pages.
        And methods which this pages returned
        Attributes:
            ip: server ip
            port: server port
            And logger of library can call'd like self.logger
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.file_path = os.path.abspath(os.path.dirname(__file__))
        self.setting_file_path = os.path.join(
            self.file_path, "setting", "setting.ini")
        self.dict_search_sys = self.setting_search_sys()
        self.ip, self.port = self.setting_connect()
        super(MyServer, self).__init__(self.ip, self.port)
        self.host_ip_table = self.create_host_ip_table()

    def create_host_ip_table(self):
        table = {}
        for k, v in SETTINGS.items():
            ip = socket.gethostbyname(v["host"])            
            pat = re.search("\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}", str(ip))
            if pat is not None:
                self.logger.error(v["host"]+" >> "+ str(ip))
                table[v["host"]] = ip
            else:
                self.logger.error("DNS Error")
                self.logger.error(str(ip))

        self.logger.debug("ip take from host is OK")
        return table

    def main_page(self, request):
        with open("forms.html", "r") as fp:
            data = fp.read()
        data = self.rewrite_main_file(data)
        return HttpResponse(data, content_type='html')

    def meta_search(self, request):
        sp = request.path.split("?")[1].split("&")
        req = {}
        for s in sp:
            tmp = s.split("=")
            req[tmp[0]] = tmp[1]

        if req["q"] == "":
            return self.main_page(request)

        req_req = req["q"].split("+")
        try:
            output = main_import(request=req_req, number="20",
                                 search_sys_dict=self.dict_search_sys,
                                 host_ip_table=self.host_ip_table)
        except HttpErrors as e:
            return e.geterr()
        else:
            return HttpResponse(output, content_type='text/html')

    def styles(self, request):
        path = os.path.join(os.getcwd(), request.path[1:])
        try:
            with open(path, "r") as fp:
                data = fp.read()

        except FileNotFoundError as e:
            self.logger.error(e)
        else:
            if b"bootstrap.js" in request.text:
                return HttpResponse(data,
                                    content_type='application/javascript')
            elif b"favicon.ico" in request.text:
                return HttpResponse(data, content_type='image/x-icon')
            else:
                return HttpResponse(data, content_type='text/css')

    def post(self, request):
        data = ""        
        for k, v in request.POST.items():
            data += str(k) + "   " + str(v)+"\r\n"
        return HttpResponse(data, content_type='html')

    def configure(self):
        self.add_route(r'^/$', self.main_page)
        self.add_route(r'^/search$', self.meta_search)
        self.add_route(r'^/form/.*$', self.styles)
        self.add_route(r'^/post$', self.post, ["POST"])

    def rewrite_main_file(self, file):
        newline = re.sub("http://[^/]+/search", "http://" +
                         str(self.ip) + ":" + str(self.port) + "/search", file)
        return newline

    def setting_search_sys(self):
        config = configparser.ConfigParser()
        config.read(self.setting_file_path)
        system = list(SETTINGS.keys())
        if "searchsystem" in config:
            conf = config['searchsystem']
            if len(system) == len(set(system) & set(list(conf))):
                return {el: conf[el] for el in system}

            else:
                config.remove_section('searchsystem')
                config['searchsystem'] = {el: "on" for el in system}
                with open(self.setting_file_path, 'w') as configfile:
                    config.write(configfile)
                return {el: conf[el] for el in system}

        else:
            config['searchsystem'] = {el: "on" for el in system}
            with open(self.setting_file_path, 'w') as configfile:
                config.write(configfile)
            return {el: config['searchsystem'][el] for el in system}

    def setting_connect(self):
        config = configparser.ConfigParser()
        config.read(self.setting_file_path)
        if "DEFAULT" in config:
            conf = config['DEFAULT']
            if 'ip' in conf and 'port' in conf:
                self.logger.info("Setting is ok")
                return(conf["ip"], int(conf["port"]))

            else:
                self.logger.info(
                    "Setting file is broken."
                    " Start server on default setting 127.0.0.1:8080")
                return("127.0.0.1", int("8080"))
        else:
            self.logger.info(
                "Setting file is broken."
                " Start server on default setting 127.0.0.1:8080")
            return("127.0.0.1", int("8080"))

try:    
    logging.config.fileConfig(
        os.path.join(os.getcwd(), "setting", "logging.conf"))
    app = MyServer()
    app.logger.info("serv start in " + str(os.getpid()))
    app.logger.info(str(app.ip) + " : " + str(app.port))
    app.serve_forever()
    app.logger.info("Cry Baby")

except OSError as e:
    app.logger.error('OSError ' + str(e.errno) + " " + os.strerror(e.errno))
