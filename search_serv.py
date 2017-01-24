import os.path
import os
import sys
import re
import logging
import logging.config
from subprocess import Popen, PIPE, STDOUT, call
from search_resp import main_import
from search_resp import SETTINGS
import configparser
from httpserver import BaseServer, HttpResponse


class MyServer(BaseServer):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.file_path = os.path.abspath(os.path.dirname(__file__))
        self.setting_file_path = os.path.join(
            self.file_path, "setting", "setting.ini")
        self.dict_search_sys = self.setting_search_sys()
        ip, port = self.setting_connect()
        super(MyServer, self).__init__(ip, port)

    def main_page(self, request):
        with open("forms.html", "r") as fp:
            data = fp.read()
        return HttpResponse(data, content_type='html')

    def notfound(self, request, name):
        with open("pages/418.html", "r") as fp:
            data = fp.read()
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
        output = main_import(request=req_req, number="20", search_sys_dict=self.dict_search_sys)
        return HttpResponse(output, content_type='text/html')

    def styles(self, request):
        path = os.path.join(os.getcwd(), request.path[1:])
        try:
            with open(path, "r") as fp:
                data = fp.read()

        except Exception as e:
            app.logger.error(e)
        else:
            if b"bootstrap.js" in request.text:
                return HttpResponse(data,
                                    content_type='application/javascript')
            elif b"favicon.ico" in request.text:
                return HttpResponse(data, content_type='image/x-icon')
            else:
                return HttpResponse(data, content_type='text/css')

    def configure(self):
        self.add_route(r'^/$', self.main_page)
        self.add_route(r'^/search$', self.meta_search)
        self.add_route(r'^/form/.*$', self.styles)
        #self.add_route(r'^/(.*)$', self.notfound)

    def rewrite_setting_file(self, file, conf):
        newline = re.sub("http://[^/]+/search", "http://" +
                         conf["ip"] + ":" + conf["port"] + "/search", file)
        with open(os.path.join(self.file_path, "forms.html"), "w") as fp:
            file = fp.write(newline)
        self.logger.info("Setting is broken. Rewrite setting")
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
                with open(os.path.join(self.file_path, "forms.html"), "r") as fp:
                    file = fp.read()

                what = re.findall("http://([^/]+)/search", file)
                for el in what:
                    ip, port = el.split(":")
                    if ip == conf["ip"] and port == conf["port"]:
                        pass
                    else:
                        newline = self.rewrite_setting_file(file, conf)
                        break
                self.logger.info("Setting is ok")
                return(conf["ip"], int(conf["port"]))

            else:
                conf = config['DEFAULT']
                conf["ip"] = '127.0.0.1'
                conf["port"] = "8181"
                with open(self.setting_file_path, 'w') as configfile:
                    config.write(configfile)

                with open(os.path.join(self.file_path, "forms.html"), "r") as fp:
                    file = fp.read()
                newline = self.rewrite_setting_file(file, conf)

            return(conf["ip"], int(conf["port"]))
        else:
            config['DEFAULT'] = {'ip': '127.0.0.1', 'port': "8080"}
            with open(self.setting_file_path, 'w') as configfile:
                config.write(configfile)

            with open(os.path.join(self.file_path, "forms.html"), "r") as fp:
                file = fp.read()
            newline = self.rewrite_setting_file(file, conf)
            return('127.0.0.1', 8080)

app = MyServer()
logging.config.fileConfig(os.path.join(os.getcwd(), "setting", "logging.conf"))

app.logger.info("start >> " + str(os.getpid()))
app.serve_forever()
