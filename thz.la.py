#!/usr/local/bin/python3
### thz.la.py

import re
import os
import io
import sys
import glob
import collections
import traceback

from discuz import Discuz
from chrome import DownloadCompleteEvent 

from selenium.webdriver.common.by import By

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tor.settings")
import django
django.setup()
import lister.models as models

class ThzCrawler(Discuz):
    BASE_URL = 'http://thz.la/'

    def OnAttachement(self, tlink):
        numRetry = 0
        av = self._avData
        while numRetry < self.MAX_RETRY:
            try:
                self._chrome.execute_script('arguments[0].click();', tlink)
                dnlink = self.WaitElementClickable(By.PARTIAL_LINK_TEXT, '立即下载附件')
                #print(dnlink.text, dnlink.get_attribute('href'))
                break
            except Exception:
                print('timeout!! retry({0}) to download'.format(numRetry))
            numRetry += 1

        if numRetry == self.MAX_RETRY:
            print('Download Failed: {}'.format(av['product']))
            return

        if glob.glob(av['path'] + '/*.torrent') :
            print('torrent already exists!')
            return

        self.SetDownloadDir(av['path'])
        dnlink.click()
        DownloadCompleteEvent(av['path']).WaitComplete()

    def ExtractSensoredJavInfo(self, titleText):
        av = self._avData
        match = re.search('\[(.*)\](.*)', titleText, re.ASCII)
        av['product'], av['title'] = match.group(1), match.group(2)
        av['studio'] = av['product'].split('-')[0]

    def ExtractUnSensoredJavInfo(self, titleText):
        av = self._avData
        match = re.search('(.*?) ([\w\-].*?) (.*)', titleText, re.ASCII)
        av['product'], av['title'] = match.group(2), match.group(3)
        if av['product'] >= '0' and av['product'] <= '9':
            av['studio'] = av['product'].split('-')[-1]
        elif 'heydouga' in av['product'] : 
            av['studio'] = 'heydouga'
        else:
            av['studio'] = re.split('_|-', av['product'])[0]

    def OnTitle(self, titleText):
        if self._board is models.Board.UnsensoredJAV:
            self.ExtractUnSensoredJavInfo(titleText) 
        elif self._board is models.Board.SensoredJAV: 
            self.ExtractSensoredJavInfo(titleText)

    def Start(self):
        self._chrome.get(self.BASE_URL)

        #test  = { Board.SensoredJAV,  'test' }
        boardList = { 
            models.Board.SensoredJAV : { 
                'name' : '亚洲有碼原創', 
                'href' : ''},
#                'pidFilter' : ('abp', 'ssni', 'ofje', 'adn', 'ipx', 'pppd')},
            models.Board.UnsensoredJAV : {
                'name' : '亚洲無碼原創',
                'href' : ''},
#                'splitter' : splitUnsensoredTitle }, 
#            models.Board.UnsensoredWestern : { 
#                'name' : '欧美無碼', 
#                'href' : '',
#                'splitter' : splitWesternTitle }
        }

        self._avData['idSite'] = 1
        self._skipExistDir = True
        self.StartCrawling(boardList)

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

