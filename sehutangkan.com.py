#!/usr/local/bin/python3
### thz.la.py

import re
import os
import io
import sys
import requests
import collections
import traceback

from discuz import Discuz

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tor.settings")
import django
django.setup()
import lister.models as models

class Sehutangkan(Discuz):
    BASE_URL = 'http://sehutangkan.com/'

    def ExtractSensoredJavInfo(self, titleText):
        av = self._avData
        match = re.search('(.*?) (.*)', titleText, re.ASCII)
        av['product'], av['title'] = match.group(1), match.group(2)
        av['studio'] = av['product'].split('-')[0]
        return True

    def ExtractUnSensoredJavInfo(self, titleText):
        av = self._avData
        match = re.search('(\S+) (\S+) (\S+) (.+)',
                titleText, re.ASCII)
        if match.group(2)  ==  '最新':
            av['product'], av['title'] = match.group(3), match.group(4)
        else:
            av['product'], av['title'] = match.group(2), match.group(3)

        if av['product'][0] >= '0' and av['product'][0] <= '9':
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

    def Start(self, numPages = None):
        #self._pageExcluded = [1, 2]
        self._chrome.get(self.BASE_URL + 'forum.php')
        if numPages:
            self.MAX_PAGE = numPages

        boardList = { 
            models.Board.SensoredJAV : { 
                'name' : '亚洲有码原创', 
                'href' : ''
            },
            #'pidFilter' : ('abp', 'ssni', 'ofje', 'adn', 'ipx', 'pppd')},
            models.Board.UnsensoredJAV : {
                'name' : '亚洲无码原创',
                'href' : ''
            }
        }
        self._avData['idSite'] = 2
        self.StartCrawling(boardList)

if __name__ == '__main__':
    thz = None
    try:
       thz = Sehutangkan()
       if len(sys.argv) > 1:
           thz.Start(int(sys.argv[1]))
       else:
           thz.Start()
    except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_tb)
    finally:
        thz.Exit();

