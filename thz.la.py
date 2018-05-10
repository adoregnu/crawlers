#!/usr/bin/python3
### thz.la.py
import re
import os
import sys
import glob
import time
import pprint
import requests
import collections
import traceback

from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
# available since 2.4.0
from selenium.webdriver.support.ui import WebDriverWait
# available since 2.26.0
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Board(Enum):
    SensoredJAV       = 1
    UnsensoredJAV     = 2
    UnsensoredWestern = 3

class DownloadCompleteEvent(FileSystemEventHandler):
    _complete = False
    def on_moved(self, event):
        print(event.dest_path + ' downloaded')
        self._complete = True

    def is_complete(self):
        return self._complete

class ThzCrawler:
    BASE_URL = 'http://taohuabt.cc/'
    MAX_PAGE = 1
    MAX_RETRY = 5
    DOWNLOAD_TIMEOUT_SEC = 5.0

    _board = '.'
    _chrome = None
    _date = None
    _printOnly = False # do not download actual file
    _stopOnFirstArticle = False # process only one article per each page
    _stopOnExistingDir = True # stop download if it's already exists

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument('blink-settings=imagesEnabled=false')
        options.add_argument('disable-popup-blocking')

        self._chrome = webdriver.Chrome('chromedriver', chrome_options=options,
                service_args=['--verbose', '--log-path=./chromedriver.log'])

    def SetDownloadDir(self, path):
        #add missing support for chrome "send_command"  to selenium webdriver
        self._chrome.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')

        params = {
            'cmd': 'Page.setDownloadBehavior',
            'params': {'behavior': 'allow', 'downloadPath': path}
        }
        self._chrome.execute("send_command", params)

    def WaitElementLocate(self, by, locate):
        return WebDriverWait(self._chrome, 10).until(
                EC.presence_of_element_located((by, locate))
        )

    def WaitElementClickable(self, by, locate):
        return  WebDriverWait(self._chrome, 10).until(
                EC.element_to_be_clickable((by, locate))
        )

    def GetPath(self, pid):
        if self._date:
            return '{0}/{1}/{2}/{3}'.format(os.getcwd(), self._board.name, self._date, pid)
        else:
            return '{0}/{1}/{2}/{3}'.format(os.getcwd(), self._board.name, pid)


    def CreateDir(self, pid):
        path = self.GetPath(pid)
        try: 
            os.makedirs(path)
        except OSError:
            return False
        return True

    def SaveImages(self, pid, imgs):
        num = 0
        for img in imgs:
            url = img.get_attribute('file')
            #print(url)
            if 'thzimg' not in url and 'thzpic' not in url:
                continue

            path = '{0}/{1}_{2}{3}'.format(
                    self.GetPath(pid), pid, num, os.path.splitext(url)[1])
            num += 1

            if self._printOnly:
                continue
            if os.path.exists(path) :
                continue

            numRetry = 0 
            while numRetry < self.MAX_RETRY:
                try:
                    res = requests.get(url)
                    with open(path, 'wb') as f:
                       f.write(res.content)
                    break
                except :
                    print('timeout!! retry{0} to save image :{1}'.format(numRetry, url))

                numRetry += 1

            if numRetry < self.MAX_RETRY:
                print(path + ' saved')
    
    def SaveTorrentFile(self, pid, tlink):
        #print(tlink.text, tlink.get_attribute('href'))
        self._chrome.execute_script('arguments[0].click();', tlink)

        dnlink = self.WaitElementClickable(By.PARTIAL_LINK_TEXT, '立即下载附件')
        #print(dnlink.text, dnlink.get_attribute('href'))

        targetPath = self.GetPath(pid)
        #print('{0}/{1}'.format(targetPath, tlink.text))
        if self._printOnly:
            return

        if glob.glob(targetPath + '/*.torrent') :
            return

        self.SetDownloadDir(targetPath)
        dnlink.click()

        observer = Observer()
        evt = DownloadCompleteEvent()
        observer.schedule(evt, path = targetPath)
        observer.start()

        elapsed = 0.0
        while not evt.is_complete() and self.DOWNLOAD_TIMEOUT_SEC > elapsed:
            time.sleep(0.2)
            elapsed += 0.2

    def ProcessOnePage(self, pid, href):

        print('Processing [{0}], title:[{1}]'.format(pid, href[1]))
        self._chrome.get(href[0])
        self.WaitElementLocate(By.ID, 'scrolltop')

        imgList = self._chrome.find_elements_by_css_selector('img[id*=aimg_]')
        td = imgList[0].find_element_by_xpath(".//ancestor::td");
        search = None
        if self._board is Board.SensoredJAV :
            search = re.findall('([0-9/]{10})', td.text, re.ASCII)
        else: 
            search = re.findall('([0-9\-]{10})', td.text, re.ASCII)

        self._date = search[len(search) - 1].replace('/', '-') if search else None

        if not self.CreateDir(pid) and self._stopOnExistingDir:
            return False

        self.SaveImages(pid, imgList)

        numRetry = 0
        while numRetry < self.MAX_RETRY:
            try:
                tlinks = self._chrome.find_elements_by_partial_link_text('.torrent')
                for tlink in tlinks:
                    self.SaveTorrentFile(pid, tlink)
                break
            except TimeoutException:
                print('timeout!! retry({0}) to download {1}'.format(numRetry, pid))
            numRetry += 1
        return True

    def ProcessThreadList(self, items, splitFn):
        urls = collections.OrderedDict()
        for tbody in items:
            link = tbody.find_element_by_css_selector('a.s.xst')
            pid, title = splitFn(link.text) 
            if not pid or not title:
                break

            if self._board is Board.UnsensoredWestern:
                em_a = tbody.find_element_by_xpath('tr/th/em/a')
                pid = '{0}-{1}'.format(em_a.text, title.replace(' ', '_'))

            urls[pid] = (link.get_attribute('href'), title)
            print('pid:[{0}], title:[{1}]'.format(pid, title))

        #pprint.pprint(urls)

        num = 0
        for pid, href in urls.items():

            if not self.ProcessOnePage(pid, href):
                print('latest update, skip {0}'.format(self._board.name))
                break
            if self._stopOnFirstArticle:
                break

    def ProcessBoard(self, board, title):
        self._board = board
        nextLink = title['href']

        pageNum = 1
        while pageNum <= self.MAX_PAGE:
            print(nextLink)
            self._chrome.get(nextLink)

            #next page link
            nextLink = self.WaitElementLocate(By.LINK_TEXT, '下一页').get_attribute('href')
            elms = self._chrome.find_elements_by_css_selector('tbody[id*=normalthread_]')
            #pprint.pprint(xlist)
            self.ProcessThreadList(elms, title['splitter'])

            pageNum += 1
            print('')

    def Exit(self, msg = ''):
        print(msg)
        self._chrome.quit()
        sys.exit(0)

    def Start(self):
        self._chrome.get(self.BASE_URL + 'forum.php')

        def splitSensoredTitle(text):
            search = re.search('\[(.*)\](.*)', text)
            return search.group(1), search.group(2)

        def splitUnsensoredTitle(text):
            #2018-05-03 050318_681-1pon 下着が最高に似合うカテキ-佐々木ゆき
            #2018-05-03 050218_680-1pon モデルコレクション 渋谷ひとみ
            #2018-05-04 [女体のしんぴ] nyoshin_n1677 めい
            #'?' after '*' means non-greedy matching
            search = re.search('(.*?) ([\w\-].*?) (.*)', text, re.ASCII)
            return search.group(2), search.group(3)

        def splitWesternTitle(text):
            search = re.search('(.*?) (.*)', text, re.ASCII)
            return search.group(1), search.group(2)

        #test  = { Board.SensoredJAV,  'test' }
        boardList = { 
            Board.SensoredJAV : { 
                'name' : '亚洲有碼原創', 
                'href' : '',
                'splitter' : splitSensoredTitle },
            Board.UnsensoredJAV : {
                'name' : '亚洲無碼原創',
                'href' : '',
                'splitter' : splitUnsensoredTitle }, 
            Board.UnsensoredWestern : { 
                'name' : '欧美無碼', 
                'href' : '',
                'splitter' : splitWesternTitle }
        }

        try:
            for board, title in boardList.items():
                name = self._chrome.find_element_by_link_text(title['name'])
                title['href'] = name.get_attribute('href')

            for board, title in boardList.items():
                self.ProcessBoard(board, title)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            self.Exit();

if __name__ == '__main__':

    thz = ThzCrawler()
    thz.Start()
