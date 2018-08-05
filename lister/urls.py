from django.urls import path

from . import views

"""
    /thzla/sensored/ssni/page-1
    /thzla/unsensored/1pon/page-1
    /onejava/ssni/page-1
"""
urlpatterns = [
    path('', views.index),
    path('<int:site>/', views.index),
    path('<int:site>/<int:board>/', views.index),
    path('<int:site>/<int:board>/<int:studio>/', views.index),
    path('<int:site>/<int:board>/<int:studio>/<int:page>/', views.index)
]

