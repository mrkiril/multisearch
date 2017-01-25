#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Task: metasearch
#
# Search through several search engines
# and merge result into HTML SERP page

# TODO: implement it here
import os.path
import os
import re
import sys
import time
from time import sleep
import socket
import base64
import hashlib
import logging
#sys.path.insert(0, "F:\Python\http")
from urllib.parse import quote
from urllib.parse import unquote
from httpclient import HttpClient
import multiprocessing
#from multiprocessing import Queue
from itertools import repeat

my_headers = [
    ('User-Agent', "Opera/9.80 (iPhone; Opera Mini/7.0.4/28.2555; U; fr)"
        " Presto/2.8.119 Version/11.10"),
    ('X-From', 'UA')]
my_user_pass = ('kiril', 'supersecret')
file_path = os.path.abspath(os.path.dirname(__file__))

client = HttpClient(
    # load cookie from file before query
    load_cookie=os.path.join(file_path, 'cookie.txt'),
    # save cookie to file after query
    save_cookie=os.path.join(file_path, 'cookie.txt'),
    connect_timeout=10,         # socket timeout on connect
    transfer_timeout=30,        # socket timeout on send/recv
    max_redirects=10,           # follow Location: header on 3xx response
    set_referer=True,           # set Referer: header when follow location
    keep_alive=3,               # Keep-alive socket up to N requests
    headers=my_headers,         # send custom headers
    http_version="1.1",         # use custom http/version
    auth=my_user_pass,          # http auth
    retry=5,                    # try again on socket or http/5xx errors
    retry_delay=10)             # wait betweet tries


SETTINGS = {

    'google': {
        'url': 'http://www.google.com.ua/search',
        'list_start': '<div id="ires"><ol>',
        'list_end': '</div></ol></div></div></div>',
        'element': '<div class="g">',
        'link': '<h3 class="r">',
        'citat': '<span class="st">',
        'iterator': '10',
        'start_number': '0',
        'sign': "q",
        'key': 'start',  # повинен бути 0 , 10 ,20, 30
        "val": {"btnG": "%D0%9F%D0%BE%D0%B8%D1%81%D0%BA"}
    },

    'mail': {
        'url': 'http://go.mail.ru/msearch',
        'list_start': '<ol class="result">',
        'list_end': '</ol><!-- FOUND: END -->',
        'element': '<li id="js-result_',
        'link': '<span class="result__title',
        'citat': '<span class="result__snp">',
        'iterator': '10',
        'start_number': '0',
        'sign': "q",
        'key': 'sf',  # повинен бути 0, 1 ,2,3,4,5
        "val": {"fm": "1", "frm": "jsok"}
    },

    'sputnik': {
        'url': 'http://www.sputnik.ru/search',
        'list_start': '<div class="b-results js-results">',
        'list_end': '</div><div class="b-paging">',
        'element': '<a data-metrics=',
        'header': '<div class="b-result-title">',
        'link': '<div class="b-result-site">',
        'citat': '<div class="b-result-tex',
        'iterator': '10',
        'start_number': '1',
        'sign': "q",
        'key': 'from',  # повинен бути 1, 11 ,21,31,41,51
        "val": {}
    },

    'yahoo': {
        'url': 'http://search.yahoo.com/search',
        'list_start': '</style><section class="reg searchCenterMiddle">',
        'list_end': '</section></section>',
        'element': '<section class="dd algo',
        'citat': '<p class="lh-20 fbox-lc2 d-box ov-h fbox-ov">',
        'link': '<div class="compTitle options-toggle">',
        'iterator': '10',
        'start_number': '1',
        'sign': "p",
        'key': 'b',  # повинен бути 1 , 11 ,21, 31
        "val": {"pz": "10", "bct": "0", "ei": "UTF-8", "gbv": "1"}
    },

    'bing': {
        'url': 'http://www.bing.com/search',
        'list_start': '<ol id="b_results"',
        'list_end': '</ol><ol id="b_context" ',
        'element': '<li class="b_algo',
        'link': '<h2',
        'citat': '<div class="b_caption">',
        'iterator': '10',
        'start_number': '1',
        'sign': "q",
        'key': 'first',  # повинен бути 1 , 11 ,21, 31
        "val": {"go": "%d0%9f%d0%be%d0%b8%d1%81%d0%ba", "qs": "ds"}
    }
}


class SearchEngine:

    def __init__(self, settings):
        self.url = settings["url"]
        self.list_start = settings["list_start"]
        self.list_end = settings["list_end"]
        self.citat = settings["citat"]
        self.val = settings["val"]
        self.link = settings["link"]
        self.element = settings["element"]
        self.sign = settings["sign"]

        self.header = None
        if 'header' in settings:
            self.header = settings['header']
        #- - - - - page changes - - - - -
        self.iterator = settings["iterator"]
        self.start_number = settings["start_number"]
        self.key = settings["key"]
        #- - - - -
        self.del_pattern = re.compile(
            "</?(b|strong|span|br|p|div|li|i)>|<(span|p|i|div|b|wbr|ul).*?>")
        self.file_path = os.path.abspath(os.path.dirname(__file__))

    def querry_constr(self, url, query, payload):
        q = url + "+".join(query)
        q += "&" + "&".join([k + "=" + v for k, v in payload.items()])
        return q

    def get_link(self, block):
        m_link = re.search(
            '''<a.*?href=".*?((http[^"]*).*?)>(.*?)</a>''', block, re.DOTALL)

        res_link = ""
        res_link = m_link.group(2)
        res_link = unquote(res_link)
        m_link_header = self.del_pattern.sub('', m_link.group(3))

        if self.header is not None:
            back_header = re.split("[ ]", self.header)
            back_header = "</" + back_header[0][1:] + ">"
            head_patt = re.search(self.header + ".*?" + back_header, block)
            m_link_header = head_patt.group()

        return (res_link, m_link_header)

    def block_finder(self, text):
        list_ = []
        try:
            if self.element[-1] != ">":
                m_find = re.finditer(self.element + ".*?>", text, re.DOTALL)

            if self.element[-1] == ">":
                m_find = re.finditer(self.element, text, re.DOTALL)

            m_find = list(m_find)
            for m in range(len(m_find)):
                list_.append(
                    text[m_find[m].span()[0]: m_find[m + 1].span()[0]])

        except IndexError as e:
            list_.append(text[m_find[-1].span()[0]:])

        return list_

    def query_to(self, query, max_count):
        payload = self.val
        arr = []  # масив лінків, описів і цитат
        for index in range((int(max_count) // 10)):
            payload[self.key] = str(
                int(self.start_number) + index * int(self.iterator))
            payload[self.sign] = str("+".join(query))
            res = client.get(self.url,
                             params=payload,
                             nonblocking=True,
                             output=os.path.join(os.getcwd(),
                                                 "socket_page.html"))
            arr.append(res)
        return arr

    def parser(self, res):
        results = []  # масив лінків, описів і цитат
        page_elements_numbers = 0
        # Повторення запитів на пошукову систему
        if res.issend == True:
            data = res.body

            if self.list_start[-1] == ">":
                # видідили список результатів
                m_pattern = re.search(
                    self.list_start + ".*?" + self.list_end, data, re.DOTALL)

            if self.list_start[-1] != ">":
                # видідили список результатів
                m_pattern = re.search(
                    self.list_start + ".*?>" + ".*?" +
                    self.list_end, data, re.DOTALL)

            if True:
                if m_pattern is not None:
                    m_block = self.block_finder(m_pattern.group())

                else:
                    return None

            for elem in m_block:  # Аналіз кожного елемента видачі
                this_elem = elem
                cheсk_link = False
                cheсk_citat = False
                cheсk_ci = re.search(self.citat, this_elem)
                if cheсk_ci is not None:
                    cheсk_citat = True

                cheсk_li = re.search(self.link, this_elem)
                if cheсk_li is not None:
                    cheсk_link = True

                if cheсk_link == False or cheсk_citat == False:
                    return None

                tmp_get = self.get_link(this_elem)
                m_link_link = tmp_get[0]
                m_link_header = tmp_get[1]

                # Create back TEG
                back_header = re.split("[ ]", self.citat)
                back_header = "</" + back_header[0][1:] + ">"
                pattern_citat = re.compile(
                    self.citat + ".+?" + back_header, re.DOTALL)

                m_citat = pattern_citat.search(this_elem)
                #last = re.search('.*$', this_elem)
                if m_citat is not None:
                    citat_str = m_citat.group()
                else:
                    citat_str = "None Citat"

                m_citat_citat = self.del_pattern.sub('', citat_str)
                elem_index_of = (1 / (1 + page_elements_numbers**2))
                page_elements_numbers += 1

                results.append([m_link_link, m_link_header,
                                m_citat_citat, elem_index_of])

        return results


class ResultsMerger:

    def __init__(self, engines):
        self.arr_engines = engines

    def getinstance(self, dick, elem):
        for k, v in dick.items():
            if elem in v:
                return k

    def search(self, query, output, max_count):
        global_start_time = time.time()
        all_ = []
        arr_obj = []
        obj_res_dick = {}
        # create stack instance of the class
        for elem in self.arr_engines:
            stack = elem.query_to(query, max_count)
            arr_obj.extend(stack)
            obj_res_dick[elem] = stack

        recv_time = time.time()
        # Take message body
        while True:
            arr_status = [ob.isready() for ob in arr_obj]
            if False in arr_status:
                sleep(0.05)
                if time.time() - global_start_time > 3.5:
                    break
                if time.time() - global_start_time > 0.9:
                    count = arr_status.count(True)
                    if count / len(arr_status) > 0.6:
                        break
                    else:
                        continue
                continue
            else:
                break

        logger.info("all time: " + str(time.time() - global_start_time))

        # parse res obj and take page data
        for ob in arr_obj:
            val = SearchEngine.parser(self.getinstance(obj_res_dick, ob), ob)
            if val is not None:
                all_.extend(val)

        logger.info("Count Q: " + str(len(all_)))
        for i in range(len(all_)):
            iteration = i + 1
            stop = False
            while not stop:
                try:
                    if all_[i][0] == all_[iteration][0]:
                        all_[i][3] += all_[iteration][3]
                        del all_[iteration]
                    else:
                        iteration += 1

                except IndexError as e:
                    break

        sort_all = sorted(all_, key=lambda x: x[3], reverse=True)
        new_all = sort_all[:]
        Number_of_page_elem = 0

        with open(output, "w", encoding='utf-8') as fp:
            fp.write(''' 
                <style>
                    h3 {
                        font-family: Arial, sans-serif;
                        margin: 5px; 
                    } 
                    p {
                        font-family: Verdana, Arial, Helvetica, sans-serif;
                        margin: 5px; 
                    }
                    .g{
                        margin: 5px;
                        padding: 10px;
                        font-size: 14px;
                        line-height: 20px;
                        background: #f5f5f5;
                        padding: 0 20px;
                        font-family: Arial, sans-serif;
                        
                    }
                    .marg{
                        margin-left:50px;
                        font-size: 16px;
                    }
                </style>
            ''')
        with open(output, "a", encoding='utf-8') as fp:
            for al in new_all[:int(max_count)]:
                # INDEX
                fp.write('''<div class="g">''')
                fp.write("<p>№ " + str(Number_of_page_elem) +
                         '''\t<span class="marg">Index:''' +
                         str(al[3]) +
                         "</span></p>")
                # Link
                fp.write("<h3><a href=" +
                         str(al[0]) + ">" + str(al[1]) + "</a></h3>")
                # Citat
                fp.write("<p>" + str(al[2]) + "</p>")
                fp.write("</div>")
                fp.write("<br><br>")
                Number_of_page_elem += 1
        with open(output) as fp:
            page = fp.read()
        return page


def main_console():
    logger = logging.getLogger(__name__)
    engines = []
    for key, value in SETTINGS.items():
        engines.append(SearchEngine(SETTINGS[key]))
        logger.info(SETTINGS[key])

    merger = ResultsMerger(engines)
    max_count = sys.argv[1]
    query = sys.argv[2:]

    output = os.path.join(os.getcwd(), 'output.html')
    page = merger.search(query, output, max_count)
    sys.stdout.write(page)


def main_import(request, number, search_sys_dict):
    global logger
    logger = logging.getLogger(__name__)
    engines = []
    rewrite_setting = {k: SETTINGS[k]
                       for k, v in search_sys_dict.items() if v == "on"}

    for key, value in rewrite_setting.items():
        engines.append(SearchEngine(SETTINGS[key]))
        logger.info(key)

    merger = ResultsMerger(engines)
    query = request
    max_count = number

    output = os.path.join(os.getcwd(), 'output.html')
    page = merger.search(query, output, max_count)
    return page

if __name__ == '__main__':
    main_console()
