#!/usr/bin/env python3
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
import logging
from urllib.parse import unquote
from httpclient import HttpClient
from httpserver import HttpErrors

my_headers = [
    ('User-Agent', "Opera/9.80 (iPhone; Opera Mini/7.0.4/28.2555; U; fr)"
        " Presto/2.8.119 Version/11.10"),
    ('X-From', 'UA')]
my_user_pass = ('kiril', 'supersecret')
file_path = os.path.abspath(os.path.dirname(__file__))

client = HttpClient(
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
        'host': 'www.google.com.ua',
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
        'host': 'go.mail.ru',
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
        'host': 'www.sputnik.ru',
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
        'host': 'search.yahoo.com',
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
        'host': 'www.bing.com',
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

    """ Class that makes an instance of each search system

        Attributes:
            self.url = search url
            self.list_start = start list of answer search system
            self.list_end = end of list
            self.citat = describe teg
            self.val = settings["val"]
            self.link = link teg
            self.element = element teg
            self.sign = sign of search

            self.iterator = number of answer in one page
            self.start_number = start number
            self.key = page key
            And logger of library can call'd like self.logger
    """

    def __init__(self, settings, host_ip_table={}):
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

        self.iterator = settings["iterator"]
        self.start_number = settings["start_number"]
        self.key = settings["key"]
        self.del_pattern = re.compile(
            "</?(b|strong|span|br|p|div|li|i)>|<(span|p|i|div|b|wbr|ul).*?>")
        self.file_path = os.path.abspath(os.path.dirname(__file__))
        self.host_ip_table = host_ip_table

    def querry_constr(self, url, query, payload):
        q = url + "+".join(query)
        q += "&" + "&".join([k + "=" + v for k, v in payload.items()])
        return q

    def get_link(self, block):
        m_link = re.search(
            '<a.*?href=".*?((http[^"]*).*?)>(.*?)</a>', block, re.DOTALL)

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
            client.host_ip_dic = self.host_ip_table
            res = client.get(self.url,
                             params=payload,                                                         
                             nonblocking=True)
            arr.append(res)
        return arr

    def parser(self, res):
        results = []  # масив лінків, описів і цитат
        page_elements_numbers = 0
        # Повторення запитів на пошукову систему
        logger.debug("is send: "+str(res.issend)+";  encoding: "+str(res.encoding))
        
        if res.issend:
            enc = ["ISO-8859-1","utf-8"]
            if res.encoding is not None:                
                enc.insert(0, str(res.encoding))
            
            for en in enc:
                try:
                    logger.debug("Try encoding with "+str(res.encoding))
                    data = res.body.decode(res.encoding)
                except UnicodeDecodeError as e:
                    logger.debug("UnicodeDecodeError "+str(res.encoding))
                    logger.debug(str(e))
                    if en == enc[-1]:
                        return None
                    continue                
                else:                    
                    break

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
                    logger.debug("M_Pattern: NONE")
                    return None

            for elem in m_block:  # Аналіз кожного елемента видачі
                this_elem = elem
                check_link = False
                cheсk_citat = False
                cheсk_ci = re.search(self.citat, this_elem, re.DOTALL)
                if cheсk_ci is not None:
                    cheсk_citat = True

                cheсk_li = re.search(self.link, this_elem, re.DOTALL)
                if cheсk_li is not None:
                    check_link = True

                if not check_link or not cheсk_citat:                    
                    continue

                tmp_get = self.get_link(this_elem)
                m_link_link = tmp_get[0]
                m_link_header = tmp_get[1]

                # Create back TEG
                back_header = re.split("[ ]", self.citat)
                back_header = "</" + back_header[0][1:] + ">"
                pattern_citat = re.compile(
                    self.citat + ".+?" + back_header, re.DOTALL)

                m_citat = pattern_citat.search(this_elem)
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
        else:
            return None
        


class ResultsMerger:

    """ Class, which makes non-blocking requests
        to the search system and return final page

        Attributes:
            And logger of library can call'd like self.logger
    """

    def __init__(self, engines, max_wait_time):
        self.arr_engines = engines
        self.max_wait_time = max_wait_time

    def getinstance(self, dick, elem):
        for k, v in dick.items():
            if elem in v:
                return k

    def search(self, query, max_count):
        global_start_time = time.time()
        all_ = []
        arr_obj = []
        obj_res_dick = {}
        # create stack instance of the class
        for elem in self.arr_engines:
            stack = elem.query_to(query, max_count)
            arr_obj.extend(stack)
            obj_res_dick[elem] = stack

        # Take message body
        obj_status_dick = {}
        while True:
            # arr_status = [ob.isready() for ob in arr_obj]
            for ob in arr_obj:
                if (ob not in obj_status_dick or
                        obj_status_dick[ob] == False):

                    obj_status_dick[ob] = ob.isready()                    
            print(obj_status_dick.values())
            lenn = len(obj_status_dick.values())
            if False in list(obj_status_dick.values()):
                sleep(0.005)
                if time.time() - global_start_time > self.max_wait_time:
                    break
                if time.time() - global_start_time > 0.8:
                    count = list(obj_status_dick.values()).count(True)
                    if count / lenn > 0.5:
                        break
                    elif True in obj_status_dick.values():
                        break
                continue
            else:
                break

        logger.info("all time: " + str(time.time() - global_start_time))
        if True not in obj_status_dick.values():
            raise HttpErrors(500)

        for ob, stat in obj_status_dick.items():            
            if stat:
                val = SearchEngine.parser(
                    self.getinstance(obj_res_dick, ob), ob)
                logger.debug("VAL is not None: "+str(val is not None))
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
        output = '''
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
            '''
        for al in new_all[:int(max_count)]:
            # INDEX
            output += '''<div class="g">'''
            output += ("<p>№ " + str(Number_of_page_elem) +
                       '''\t<span class="marg">Index:''' +
                       str(al[3]) +
                       "</span></p>")
            # Link
            output += ("<h3><a href=" +
                       str(al[0]) + ">" + str(al[1]) + "</a></h3>")
            # Citat
            output += ("<p>" + str(al[2]) + "</p>")
            output += ("</div>")
            output += ("<br><br>")
            Number_of_page_elem += 1
        return output.encode()


def main_import(request, number, search_sys_dict, 
                host_ip_table, max_wait_time):
    """ The method must import class server.
        What makes a direct request and returns the final page

        logger can call'd like logger
    """
    global logger
    logger = logging.getLogger(__name__)
    engines = []
    rewrite_setting = {k: SETTINGS[k]
                       for k, v in search_sys_dict.items() if v == "on"}

    for key, value in rewrite_setting.items():
        engines.append(SearchEngine(SETTINGS[key], host_ip_table))
        logger.info(key)

    merger = ResultsMerger(engines=engines,
                           max_wait_time=max_wait_time)
    query = request
    max_count = number
    page = merger.search(query, max_count)
    return page
