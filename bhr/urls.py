from django.conf.urls import patterns, include, url
from django.contrib import admin

from rest_framework import routers
from bhr import views

router = routers.DefaultRouter()
router.register(r'whitelist', views.WhitelistViewSet)
router.register(r'blocks', views.BlockViewset)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'api/', include(router.urls)),
)
