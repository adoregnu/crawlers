#!/usr/local/bin/python3
import os
import sys
import time
import glob

from selenium import webdriver
# available since 2.4.0
from selenium.webdriver.support.ui import WebDriverWait
# available since 2.26.0
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DownloadCompleteEvent(FileSystemEventHandler):
    _destPath = None
    _complete = False
    DOWNLOAD_TIMEOUT_SEC = 5.0

    def __init__(self, target):
        observer = Observer()
        observer.schedule(self, path = target)
        observer.start()

    def on_moved(self, event):
        print(event.dest_path + ' downloaded')
        self._complete = True 
        self._destPath = event.dest_path
        
    def GetDestPath(self):
        return self._destpath

    def WaitComplete(self):
        elapsed = 0.0
        while not self._complete and self.DOWNLOAD_TIMEOUT_SEC > elapsed:
            time.sleep(0.2)
            elapsed += 0.2

        if elapsed >= self.DOWNLOAD_TIMEOUT_SEC:
            return False
        else:
            return True

class Chrome:

    _chrome = None

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument('blink-settings=imagesEnabled=false')
        options.add_argument('disable-popup-blocking') 
        
        self._chrome = webdriver.Chrome(
            'chromedriver',
            chrome_options=options,
            service_args=['--verbose', '--log-path=./chromedriver.log']
        ) 

    def MkDir(self, path):
        try: 
            os.makedirs(path)
        except OSError:
            #print('{} : already exists'.format(path))
            return False
        return True

    def GetPath(self):
        return None
        
    def CreateDir(self):
        path = self.GetPath()
        try: 
            os.makedirs(path)
        except OSError:
            if not glob.glob(path + '/*.torrent'):
                print('no torrent file!!')
                return True
            else: 
                return False
        return True

    def SetDownloadDir(self, path):
        #add missing support for chrome "send_command"  to selenium webdriver

        self._chrome.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command') 
        params = {
                'cmd': 'Page.setDownloadBehavior',
                'params': {'behavior': 'allow', 'downloadPath': path}
        }
        self._chrome.execute("send_command", params) 
        
    def WaitElementLocate(self, by, locate):
        return WebDriverWait(self._chrome, 10).until(EC.presence_of_element_located((by, locate))) 
    
    def WaitElementClickable(self, by, locate):
        return  WebDriverWait(self._chrome, 10).until(EC.element_to_be_clickable((by, locate)))

    def Exit(self, msg = ''):
        print(msg)
        self._chrome.quit()
        sys.exit(0)
