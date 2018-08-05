from django.contrib import admin

# Register your models here.
from .models import AvData, AvStudio

admin.site.register(AvData)
admin.site.register(AvStudio)

