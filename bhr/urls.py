from django.conf.urls import patterns, include, url
from django.contrib import admin

from rest_framework import routers
from bhr import views

router = routers.DefaultRouter()
router.register(r'whitelist', views.WhitelistViewSet)
router.register(r'blocks', views.BlockViewset)
router.register(r'current_blocks', views.CurrentBlockViewset, 'current_blocks')
router.register(r'expected_blocks', views.ExpectedBlockViewset, 'expected_blocks')

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^block', views.block),
    url(r'^query/(?P<cidr>.+)', views.BlockHistory.as_view()),
    url(r'^api/', include(router.urls)),
)
