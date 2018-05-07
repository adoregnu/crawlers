#!/usr/bin/python3
### parser.py
import re
import os
import sys
import time
import pprint
import requests
import collections

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DownloadCompleteEvent(FileSystemEventHandler):
    _complete = False
    def on_moved(self, event):
        print('download complete :' + event.dest_path)
        self._complete = True

    def is_complete(self):
        return self._complete

class ThzCrawling:
    _chrome = None
    _baseUrl = 'http://taohuabt.cc/'
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

        params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': path}}
        self._chrome.execute("send_command", params)

    def WaitElementLocate(self, by, locate):
        return WebDriverWait(self._chrome, 10).until(
                EC.presence_of_element_located((by, locate))
        )

    def WaitElementClickable(self, by, locate):
        return  WebDriverWait(self._chrome, 10).until(
                EC.element_to_be_clickable((by, locate))
        )

    def CheckDir(self, pid):
        try: 
            os.mkdir(pid)
        except OSError:
            return False
        return True

    def SaveImages(self, pid, imgs):
        num = 0
        for img in imgs:
            url = img.get_attribute('file')
            if 'thumbsnap' in url:
                continue

            path = '{0}/{1}_{2}{3}'.format(pid, pid, num, os.path.splitext(url)[1])
            print(url, path)
            with open(path, 'wb') as f:
               f.write(requests.get(url).content)

            num += 1
    
    def SaveTorrentFile(self, pid, tlink):
        #print(tlink.text, tlink.get_attribute('href'))
        self._chrome.execute_script('arguments[0].click();', tlink)

        dnlink = self.WaitElementClickable(By.PARTIAL_LINK_TEXT, '立即下载附件')
        #print(dnlink.text, dnlink.get_attribute('href'))

        downloadPath = os.getcwd() + '/' + pid
        destFile = '{0}/{1}'.format(downloadPath, tlink.text)
        print(downloadPath, destFile)

        self.SetDownloadDir(downloadPath)
        dnlink.click()

        observer = Observer()
        evt = DownloadCompleteEvent()
        observer.schedule(evt, path = downloadPath)
        observer.start()

        maxTime = 5.0
        while not evt.is_complete() and maxTime > 0.0:
            time.sleep(0.2)
            maxTime -= 0.2

    def ProcessThreadList(self, items, splitFn):
        urls = collections.OrderedDict()
        for tbody in items:
            link = tbody.find_element_by_css_selector('a.s.xst')
            #print(link.text)

            pid, title = splitFn(link.text) 
            #print('pid:{0}, title:{1}'.format(pid, title))
            if not pid or not title:
                break

            urls[pid] = link.get_attribute('href')

        pprint.pprint(urls)
        print('')

        num = 0
        for pid, href in urls.items():
            if not self.CheckDir(pid): continue 

            print(pid, href)
            self._chrome.get(href)
            self.WaitElementLocate(By.ID, 'scrolltop')

            imgList = self._chrome.find_elements_by_css_selector('img[id*=aimg_]')
            #pprint.pprint(imgList)
            self.SaveImages(pid, imgList)

            tlinks = self._chrome.find_elements_by_partial_link_text('.torrent')
            for tlink in tlinks:
                self.SaveTorrentFile(pid, tlink)

    def ProcessBoard(self, title, splitFn):
        nextLink = self._chrome.find_element_by_link_text(title).get_attribute('href')

        pageNum = 1
        while pageNum < 2:
            print(nextLink)
            self._chrome.get(nextLink)

            #next page link
            nextLink = self.WaitElementLocate(By.LINK_TEXT, '下一页').get_attribute('href')
            elms = self._chrome.find_elements_by_css_selector('tbody[id*=normalthread_]')
            #pprint.pprint(xlist)
            self.ProcessThreadList(elms, splitFn)

            pageNum += 1
            print('')

    def Exit(self, msg = ''):
        print(msg)
        self._chrome.quit()
        sys.exit(0)

    def Start(self):
        self._chrome.get(self._baseUrl + 'forum.php')

        def splitSensoredTitle(text):
            search = re.search('\[(.*)\](.*)', text)
            return search.group(1), search.group(2)

        def splitUnsensoredTitle(text):
            #2018-05-03 050318_681-1pon 下着が最高に似合うカテキ-佐々木ゆき
            #2018-05-03 050218_680-1pon モデルコレクション 渋谷ひとみ
            #2018-05-04 [女体のしんぴ] nyoshin_n1677 めい
            #'?' after '*' means non-greedy matching
            search = re.search('.* ([\w\-].*?) (.*)', text, re.ASCII)
            return search.group(1), search.group(2)

        boardList = { 
#            '亚洲有碼原創' : splitSensoredTitle,
            '亚洲無碼原創' : splitUnsensoredTitle
        }

        try:
            for title, splitter in boardList.items():
                self.ProcessBoard(title, splitter)
        except:
                print(sys.exc_info())
        finally:
            self.Exit();

if __name__ == '__main__':

    thz = ThzCrawling()
    thz.Start()
