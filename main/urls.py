from django.contrib import admin
from django.urls import path
from .views import home
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", home, name="home"),
]

if settings.DEBUG:
    urlpatterns += static("pictures/", document_root=settings.SPIDER_PICTURES_DIR)
