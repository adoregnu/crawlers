#!/usr/local/bin/python3

import os
import io
import sys
import requests
import traceback

from chrome import Chrome 

from selenium.webdriver.common.by import By
# available since 2.4.0
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tor.settings")
import django
django.setup()
import lister.models as models

class Discuz(Chrome):
    MAX_RETRY = 10
    MAX_PAGE = 3

    _board = None
    _searchOnly = False
    _site = None
    _avData = {}
    _pageExcluded = []
    _skipExistDir = False
    _imageDownloaded = False
    _torrentDownloaded = False

    def OnGetTarget(self):
        return self._avData['path'], self._avData['product']

    def OnContent(self, content):
        print(self._avData)
        self._avData['board'] = self._board.value
        models.InsertAvData(self._avData)

    def OnTitle(self, titleText):
        pass

    def OnUplaodedTime(self, time):
        self._avData['uploadedTime'] = time

    def OnImage(self, url, num):
        #print(url)
        target, name = self.OnGetTarget();
        if not target: return

        path = '{0}/{1}_{2}{3}'.format(
                target, name, num, os.path.splitext(url)[1])
        if os.path.exists(path):
            print('{} already exists!'.format(path))
            return

        numRetry = 0 
        while numRetry < self.MAX_RETRY:
            try:
                res = requests.get(url, timeout=10)
                with open(path, 'wb') as f:
                    f.write(res.content)
                break
            except:
                print(sys.exc_info())
                print('Retry:{0}, {1}'.format(numRetry, url)) 

            numRetry += 1

        if numRetry < self.MAX_RETRY:
            print(path + ' saved')

    def OnAttachement(self, tlink):
        if not tlink: return
        path, _ = self.OnGetTarget();
        if not path: return

        url = tlink.get_attribute('href')
        filePath = '{0}/{1}'.format(path, tlink.text)
        if os.path.exists(filePath):
            print('{} already exists!'.format(filePath))
            return

        print('Downloading {}'.format(filePath))
       
        numRetry = 0
        while numRetry < self.MAX_RETRY:
            try:
                res = requests.get(url, timeout=10)
                with open(filePath, 'wb') as f:
                    f.write(res.content)
            except Exception as e:
                print(str(e))
                return False
            numRetry += 1

    def ParseUploadedTime(self, content):
        uploadTimeXpath = [
            'div/div/div/em/span',
            'div/div/div/em', 
        ] 
        uploadedTime = None
        for xpath in uploadTimeXpath:
            try:
                elm = content.find_element_by_xpath(xpath)
                if 'span' in xpath:
                    uploadedTime = elm.get_attribute('title')
                else: # if key == 'em'
                    tmp = elm.text.split(' ')
                    uploadedTime = ' '.join(tmp[1:])

                self.OnUplaodedTime(uploadedTime)
                break
            except NoSuchElementException as e:
                #print(str(e))
                pass

    def ParseImage(self, content):
        imgList = content.find_elements_by_css_selector('img[id*=aimg_]')
        num = 0 
        for img in imgList:
            self.OnImage(img.get_attribute('file'), num)
            num += 1

    def ParseAttachment(self, content):
        linkList = content.find_elements_by_partial_link_text('.torrent')
        for link in linkList:
            self.OnAttachement(link)

    def ParseTitle(self):
        titleXpath = '/html/body/div/div/div/table[1]/tbody/tr/td[2]'
        title = self.WaitElementLocate(By.XPATH, titleXpath)
        titleText = title.find_element_by_id('thread_subject')
        self.OnTitle(titleText.text)

        av = self._avData
        av['path'] = './{}/{}/{}/{}'.format(models.AvSite[av['idSite']]['name'],
                self._board.name, av['studio'], av['product'])
        ret = self.MkDir(av['path'])


    # True : Images and torrent are downloaded
    # False : Images and torrent are not download
    def ProcessArticle(self, href):
        #get contents
        self._chrome.get(href)

        self.ParseTitle()
        #print(self._avData)
        #return;

        contentXpath = '/html/body/div/div/div/div/table/tbody/tr/td[2]'
        content = self.WaitElementLocate(By.XPATH, contentXpath)
        self.ParseUploadedTime(content)
        self.ParseImage(content)
        self.ParseAttachment(content)
        self.OnContent(content)

    def ProcessArticles(self, articles):
        urls = []
        for article in articles:
            link = article.find_element_by_css_selector('a.s.xst')
            url = link.get_attribute('href')
            print('title:{}:{}'.format(link.text, url))
            urls.append(url)

        if self._searchOnly:
            return

        self._imageDownloaded = False
        self._torrentDownloaded = False
        num = 0
        for url in urls:
            try:
                self.ProcessArticle(url)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)
            num += 1
            #if num == 5: break

    def ProcessForum(self, link):
        nextLink = link 
        pageNum = 1
        while pageNum <= self.MAX_PAGE:
            print(nextLink)
            self._chrome.get(nextLink)

            #next page link
            articles = None
            try:
                nextLink = self.WaitElementLocate(
                        By.LINK_TEXT, '下一页').get_attribute('href')
                articles = self._chrome.find_elements_by_css_selector(
                        'tbody[id*=normalthread_]')
                if pageNum not in self._pageExcluded:
                    self.ProcessArticles(articles)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_tb)
            finally:
                pageNum  += 1

            print('')

    def StartCrawling(self, boardList):
        for board, title in boardList.items():
            name = self.WaitElementClickable(By.PARTIAL_LINK_TEXT, title['name'])
            title['href'] = name.get_attribute('href')

        for board, title in boardList.items():
            self._board = board
            if title.get('maxPages'):
                self.MAX_PAGE = title['maxPages']
            else:
                self.MAX_PAGE = 3
            self.ProcessForum(title['href'])
