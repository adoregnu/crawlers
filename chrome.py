#!/usr/local/bin/python3
import os
import sys

from selenium import webdriver
# available since 2.4.0
from selenium.webdriver.support.ui import WebDriverWait
# available since 2.26.0
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DownloadCompleteEvent(FileSystemEventHandler):
    _complete = False

    def __init__(self, target):
        observer = Observer()
        observer.schedule(self, path = target)
        observer.start()

    def on_moved(self, event):
        print(event.dest_path + ' downloaded')
        self._complete = True 
        
    def Complete(self):
        return self._complete

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
    
    def GetPath(self, pid):
        return None
        
    def CreateDir(self, pid):
        path = self.GetPath(pid)
        try: 
            os.makedirs(path)
        except OSError:
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
