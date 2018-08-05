import sys
import traceback

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q
from django.db.models import Count

from .models import AvData, AvSite, AvStudio
from qbittorrent import Client

Boards = {
    'all' : 0,
    'sensoredjav': 1,
    'unsensoredjav' : 2,
#    'unsensoredwestern' : 3,
#    'unsensoredetc' : 4 
}

def post(request):
    productId = request.POST.get('productId', None)

    qb = Client('http://bsyoo.me:9090')
    qb.login('admin', 's82ohigh')
    #torrents = qb.torrents()
    resp = 'ok'
    message = ''
    try:
        obj = AvData.objects.get(id=productId)
        for tor in obj.Torrents:
            #print(tor.path)
            with open(tor.path, 'rb') as f:
                qb.download_from_file(f)

        obj.numDownloaded += 1
        obj.save(update_fields=['numDownloaded'])
        message = str(obj.numDownloaded)
    except Exception as e:
        resp = 'fail'
        message = str(e)

    data = { 'status': resp, 'message': message }
    return JsonResponse(data)


def getAvList(siteId, boardId, studioId, pageNum):
    maxShowingPages = settings.MAX_PAGES_PER_PAGE
    maxShowingItems = settings.MAX_ITEMS_PER_PAGE

    qcond = None

    if siteId != 0:
        qcond = Q(idSite = siteId)
    if boardId != 0 :
        if qcond: qcond &= Q(boardType = boardId)
        else: qcond = Q(boardType = boardId)
    if studioId != 0:
        if qcond: qcond &= Q(studio = studioId)
        else: qcond = Q(idStudio = sutdioId)

    if not qcond:
        avList = AvData.objects
    else:
        avList = AvData.objects.filter(qcond)

    numAvs = avList.count()
    pageEnd = pageNum + 1 if pageNum >= maxShowingPages else maxShowingPages
    totalPage = int((numAvs - 1) / maxShowingItems) + 1
    if pageEnd > totalPage: pageEnd = totalPage

    pageStart = pageEnd - maxShowingPages + 1
    if pageStart < 0: pageStart = 1
    pages = list(range(pageStart, pageEnd+1))
    if pageEnd < totalPage:
        pages.append(totalPage)
    if pageStart > 1 :
        pages.insert(0, 1)

    itemStart = (pageNum - 1) * maxShowingItems
    itemEnd = itemStart + maxShowingItems

    return avList.order_by('-uploadedTime')[itemStart:itemEnd], pages

# SELECT production, COUNT(production) as count
# FROM AvData 
# WHERE boardType = boards[board]
# GROUP BY production 
def studios(site, board):
    qcond = None
    if site != 0 :
        qcond = Q(idSite = site)
    if board != 0:
        if qcond: qcond &= Q(boardType = board)
        else: qcond  = Q(boardType = board)

    if qcond:
        obj = AvData.objects.filter(qcond)
    else:
        obj = AvData.objects.all()
    
    return AvStudio.objects.filter(id__in=obj.values('studio').distinct()).order_by('nameEn')
   
# site : 0 : all, 1 : thz.la, 2 : sehutangkan
# board : 0 : all, 1 : sensored, 2: unsensored
# studio : 0 : all, 
def index(request, site=0, board = 1, studio = 0, page = 1):
    if request.method == 'POST':
        return post(request)

    avList, pageList = getAvList(site, board, studio, page)
    studioList = studios(site, board)

    context = {
        'site' : site,
        'siteList' : AvSite,
        'board' : board,
        'boardList' : Boards,
        'avList' : avList,
        'page' : page,
        'pageList' : pageList,
        'studio' : studio,
        'studioList' : studioList
    }
    return render(request, 'lister/index.html', context)
