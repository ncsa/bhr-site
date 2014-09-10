from django.conf.urls import patterns, include, url
from django.contrib import admin

from rest_framework import routers
from bhr import views

router = routers.DefaultRouter()
router.register(r'whitelist', views.WhitelistViewSet)
router.register(r'blocks', views.BlockViewset)
router.register(r'blockentries', views.BlockEntryViewset)
router.register(r'current_blocks', views.CurrentBlockViewset, 'current_blocks')
router.register(r'expected_blocks', views.ExpectedBlockViewset, 'expected_blocks')
router.register(r'pending_blocks', views.PendingBlockViewset, 'pending_blocks')
router.register(r'current_blocks_brief', views.CurrentBlockBriefViewset, 'current_blocks_brief')

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^api/', include(router.urls)),
    url(r'^api/block$', views.block),
    url(r'^api/queue/(?P<ident>.+)', views.BlockQueue.as_view()),
    url(r'^api/unblock_queue/(?P<ident>.+)', views.UnBlockQueue.as_view()),
    url(r'^api/query/(?P<cidr>.+)', views.BlockHistory.as_view()),
)
