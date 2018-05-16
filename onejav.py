#!/usr/local/bin/python3
### onejav.py

import re
import os
import sys
import glob
import time
import requests
import collections
import traceback
import chrome

from enum import Enum

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class OnejavCrawler(chrome.Chrome):
    BASE_URL = 'https://onejav.com'
    DOWNLOAD_TIMEOUT_SEC = 5.0
    MAX_RETRY = 5

    _date = None

    def GetPath(self, pid=''):
        if self._date:
            return '{0}/openjav/{1}'.format(os.getcwd(), self._date)
        else:
            return '{0}/openjav'.format(os.getcwd())

    def SaveFile(self, path, url):
        if os.path.exists(path) :
            return

        numRetry = 0
        while numRetry < self.MAX_RETRY:
            try:
                res = requests.get(url, timeout=10)
                with open(path, 'wb') as f:
                   f.write(res.content)
                break
            except :
                print('timeout!! retry{0} to save image :{1}'.format(numRetry, url))
            numRetry += 1

        if numRetry < self.MAX_RETRY:
            print(path + ' saved')

    def SaveImage(self, pid, url):
        path = '{0}/{1}{2}'.format(self.GetPath(), pid,
                os.path.splitext(url)[1])
        self.SaveFile(path, url)

    def DownloadTorrent(self, pid, url, size):
        tmp = size.split(' ')[0]

        path = '{0}/{1}-{2}G.torrent'.format(self.GetPath(), pid, tmp)
        self.SaveFile(path, url)

    def ProcessPage(self, url):
        self._chrome.get(url)
        paging = self.WaitElementLocate(By.CLASS_NAME, 'pagination')

        articles = self._chrome.find_elements_by_class_name('card')
        for article in articles:
            image = article.find_element_by_class_name('image')
            pid = article.find_element_by_xpath('div/div/div/div/h5/a')
            size = article.find_element_by_xpath('div/div/div/div/h5/span')
            self.SaveImage(pid.text, image.get_attribute('src'))

            torrent = article.find_element_by_xpath('div/div/div/div/a')
            self.DownloadTorrent(pid.text, torrent.get_attribute('href'), size.text)

        try:
            elm = paging.find_element_by_link_text('Next')
            return elm.get_attribute('href')
        except:
            print('Page ended')
            return None

    def ProcessOverview(self, url):
        self._date = url['date']
        if self.CreateDir(''):
            self.SetDownloadDir(self.GetPath())

        nextPage = url['href']
        pageNum = 1
        retry = 0
        while nextPage and retry < 3:
            print('page {0} : {1}'.format(pageNum, nextPage))
            try:
                nextPage = self.ProcessPage(nextPage)
                pageNum += 1; 
            except TimeoutException:
                retry += 1

        if retry >= 3:
            print('failed to load page:', nextPage)

    def Start(self):
        self._chrome.get(self.BASE_URL)

        urls = []
        overviewList = self._chrome.find_elements_by_class_name('overview')
        for item in overviewList:
            url = {}
            url['href'] = item.get_attribute('href')
            url['date'] = item.find_element_by_xpath('..').get_attribute('data-date')
            urls.append(url)
            print(url)

        if not os.path.exists(self.GetPath()) and not self.CreateDir(''):
            print('could not create dir!')
            return

        self.SetDownloadDir(self.GetPath())
        for url in urls:
            self.ProcessOverview(url)

if __name__ == '__main__':
    onejav = OnejavCrawler()
    try :
        onejav.Start()
    except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_tb)
    finally:
        onejav.Exit();
