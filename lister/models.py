# Create your models here.
import os
from enum import Enum
from glob import glob
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

Boards = [
    'all',
    'sensoredjav',
    'unsensoredjav',
    'unsensoredwestern',
    'unsensoredetc'
]

AvSite = [
        {'id': 0, 'url' : None, 'name' : 'all'},
        {'id': 1, 'url' : 'http://thz.la', 'name' : 'Thz.La'},
        {'id': 2, 'url' : 'http://sehutangkan.com', 'name' : 'sehutangkan'},
]

class Board(Enum):
    All               = 0
    SensoredJAV       = 1
    UnsensoredJAV     = 2
    UnsensoredWestern = 3

class AvStudio(models.Model):
    id      = models.AutoField(primary_key=True)
    nameEn  = models.CharField(max_length=20)
    company = models.CharField(max_length=100, blank=True)
    numAvIncluded = models.IntegerField(default=1)

    def __str__(self):
        return '{} : {} products'.format(self.nameEn, self.numAvIncluded)

class AvData(models.Model):
    id            = models.AutoField(primary_key=True)
    title         = models.CharField(max_length=400)
    product       = models.CharField(max_length=40)
    uploadedTime  = models.DateTimeField()
    numDownloaded = models.IntegerField(default=0)
    boardType     = models.SmallIntegerField()
    studio        = models.ForeignKey(AvStudio, on_delete=models.CASCADE)
    idSite        = models.IntegerField()

    _path = None
    def __str__(self):
        return '{0} : {1}'.format(self.product, self.title)

    def _getFiles(self, patt):
        global Boards

        if not self._path:
            self._path = '{}/{}/{}/{}/{}'.format(
                    self.Site['name' ], Boards[self.boardType],
                    self.studio.nameEn, self.product, patt)
        #print(self._path)
        return self._path

    @property
    def Site(self):
        global AvSite
        return AvSite[self.idSite]

    @property
    def Images(self):
        return sorted(glob(self._getFiles('*.jpg')))

    @property
    def Torrents(self):
        class File:
            name = None
            path = None
            def __init__(self, name, path):
                self.name = name
                self.path = path

        files = []

        for path in glob(self._getFiles('*.torrent')):
            files.append(File(os.path.basename(path), path))

        return files

def InsertAvData(av):
    avObj = None
    try:
        avObj = AvData.objects.get(product=av['product'], idSite=av['idSite'])
        print('{} already exists!'.format(av['product']))
        return
    except ObjectDoesNotExist:
        pass

    #av = self._avData
    studioObj = None
    try:
        studioObj = AvStudio.objects.get(nameEn=av['studio'])
        if not avObj:
            studioObj.numAvIncluded += 1
            studioObj.save(update_fields=['numAvIncluded'])
    except ObjectDoesNotExist:
        studioObj = AvStudio(nameEn = av['studio'])
        studioObj.save()

    AvData(title = av['title'],
        product = av['product'],
        uploadedTime = av['uploadedTime'],
        boardType  = av['board'],
        studio = studioObj,
        idSite = av['idSite']
    ).save()

