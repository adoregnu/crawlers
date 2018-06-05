#!/usr/local/bin/python3
### thz.la.py

import re
import os
import sys
import glob
import requests
import collections
import traceback

import chrome 

from enum import Enum
from selenium.webdriver.common.by import By
# available since 2.4.0
from selenium.common.exceptions import TimeoutException


class Board(Enum):
    SensoredJAV       = 1
    UnsensoredJAV     = 2
    UnsensoredWestern = 3

class ThzCrawler(chrome.Chrome):
    BASE_URL = 'http://taohuabt.cc/'
    MAX_PAGE = 3
    MAX_RETRY = 5

    _board = '.'
    _date = None

    _stopOnFirstArticle = False # process only one article per each page
    _skipExistingDir = True
    _searchOnly = False
    _printOnly = False # do not download actual file

    def GetPath(self, pid):
        if self._date:
            return '{0}/Thz.La/{1}/{2}/{3}'.format(
                    os.getcwd(), self._board.name, self._date, pid)
        else:
            return '{0}/Thz.La/{1}/{2}'.format(
                    os.getcwd(), self._board.name, pid)

    def SaveImages(self, pid, imgs):
        num = 0
        for img in imgs:
            url = img.get_attribute('file')
            #print(url)
            if not url:
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
                    res = requests.get(url, timeout=10)
                    with open(path, 'wb') as f:
                        f.write(res.content)
                    break
                except:
                    print(sys.exc_info())
                    print(' retry{0} to save image :{1}'.format(numRetry, url)) 

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

        chrome.DownloadCompleteEvent(targetPath).WaitComplete()

    def ProcessOnePage(self, pid, href):

        print('Processing [{0}], title:[{1}]'.format(pid, href[1]))

        self._chrome.get(href[0])
        self.WaitElementLocate(By.ID, 'scrolltop')

        imgList = self._chrome.find_elements_by_css_selector('img[id*=aimg_]')

        td = imgList[0].find_element_by_xpath(".//ancestor::td");
        if self._board is Board.SensoredJAV:
            patt = '([0-9/]{10})'
        else:
            patt = '([0-9\-]{10})'

        search = re.findall(patt, td.text, re.ASCII)
        if search:
            self._date = search[len(search) - 1].replace('/', '-')
       else:
            self._date = None

        if not self.CreateDir(pid) and self._skipExistingDir:
            return True

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

    def ProcessThreadList(self, items, splitFn, pidFilter):
        urls = collections.OrderedDict()
        for tbody in items:
            link = tbody.find_element_by_css_selector('a.s.xst')
            pid, title = splitFn(link.text) 
            if not pid or not title:
                print('failed parse title: skip!', link.text)
                continue

            if self._board is Board.UnsensoredWestern:
                em_a = tbody.find_element_by_xpath('tr/th/em/a')
                pid = '{0}-{1}'.format(em_a.text, title.replace(' ', '_'))

            if pidFilter :
                p = pid.split('-')
                if not p[0] in pidFilter:
                    continue

            urls[pid] = (link.get_attribute('href'), title)
            print('pid:[{0}], title:[{1}]'.format(pid, title))

        if self._searchOnly:
            return

        if len(urls) == 0 and pidFilter:
            print('pid {0} does not exist in this page.', pidFilter)

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
            self.ProcessThreadList(elms, title['splitter'], title.get('pidFilter'))

            pageNum += 1
            print('')

    def Start(self):
        self._chrome.get(self.BASE_URL + 'forum.php')

        def splitSensoredTitle(text):
            match = re.search('\[(.*)\](.*)', text)
            if match:
                return match.group(1), match.group(2)
            else:
                return None, None

        def splitUnsensoredTitle(text):
            #2018-05-03 050318_681-1pon 下着が最高に似合うカテキ-佐々木ゆき
            #2018-05-03 050218_680-1pon モデルコレクション 渋谷ひとみ
            #2018-05-04 [女体のしんぴ] nyoshin_n1677 めい
            #'?' after '*' means non-greedy matching
            search = re.search('(.*?) ([\w\-].*?) (.*)', text, re.ASCII)
            if search:
                return search.group(2), search.group(3)
            else:
                return None, None

        def splitWesternTitle(text):
            search = re.search('(.*?) (.*)', text, re.ASCII)
            if search:
                return search.group(1), search.group(2)
            else:
                return None, None

        #test  = { Board.SensoredJAV,  'test' }
        boardList = { 
            Board.SensoredJAV : { 
                'name' : '亚洲有碼原創', 
                'href' : '',
                'splitter' : splitSensoredTitle},
#                'pidFilter' : ('abp', 'ssni', 'ofje', 'adn', 'ipx', 'pppd')},
            Board.UnsensoredJAV : {
                'name' : '亚洲無碼原創',
                'href' : '',
                'splitter' : splitUnsensoredTitle }, 
#            Board.UnsensoredWestern : { 
#                'name' : '欧美無碼', 
#                'href' : '',
#                'splitter' : splitWesternTitle }
        }

        for board, title in boardList.items():
            #name = self._chrome.find_element_by_link_text(title['name'])
            name = self.WaitElementClickable(By.PARTIAL_LINK_TEXT, title['name'])
            title['href'] = name.get_attribute('href')

        for board, title in boardList.items():
            self.ProcessBoard(board, title)

if __name__ == '__main__':
    thz = None
    try:
        thz = ThzCrawler()
        thz.Start()
    except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_tb)
    finally:
        thz.Exit();

