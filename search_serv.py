import os.path
import os
import sys
import logging
import logging.config
from subprocess import Popen, PIPE, STDOUT, call
from search_resp import main_import
file_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(file_path)
from httpserver import BaseServer, HttpResponse

class MyServer(BaseServer):
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
                
        if req["q"]=="":            
            return self.main_page(request)
        
        req_req = req["q"].split("+")
        output= main_import(request=req_req, number="20")
        return HttpResponse(output, content_type='text/html')
    
    def styles(self, request):
        path = os.path.join(os.getcwd(), request.path[1:] )
        #print(os.getpid())
        try:
            with open(path, "r") as fp:
                data = fp.read()
                
        except Exception as e:
            app.logger.error(e)
        else:
            if b"bootstrap.js" in request.text:
                return HttpResponse(data, content_type='application/javascript')
            elif b"favicon.ico" in request.text:
                return HttpResponse(data, content_type='image/x-icon')            
            else:
                return HttpResponse(data, content_type='text/css')
    
    def configure(self):
        self.add_route(r'^/$', self.main_page)
        self.add_route(r'^/search$', self.meta_search)
        self.add_route(r'^/form/.*$', self.styles)
        #self.add_route(r'^/(.*)$', self.notfound)
        


app = MyServer('127.0.0.1', 8080)
logging.config.fileConfig( os.path.join(os.getcwd(),"setting", "logging.conf" ) )
 
app.logger.info("start")
app.serve_forever()
