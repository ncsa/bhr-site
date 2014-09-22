from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import patterns, include, url
from django.contrib import admin

from rest_framework import routers
from bhr import views
from bhr import browser_views

router = routers.DefaultRouter()
router.register(r'whitelist', views.WhitelistViewSet)
router.register(r'blocks', views.BlockViewset)
router.register(r'blockentries', views.BlockEntryViewset)
router.register(r'current_blocks', views.CurrentBlockViewset, 'current_blocks')
router.register(r'expected_blocks', views.ExpectedBlockViewset, 'expected_blocks')
router.register(r'pending_blocks', views.PendingBlockViewset, 'pending_blocks')
router.register(r'current_blocks_brief', views.CurrentBlockBriefViewset, 'current_blocks_brief')
router.register(r'pending_removal_blocks', views.PendingRemovalBlockViewset, 'pending_removal_blocks')

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^api/', include(router.urls)),
    url(r'^api/block$', views.block),
    url(r'^api/unblock_now$', views.unblock_now),
    url(r'^api/stats$', views.stats),

    url(r'^api/mblock$', views.mblock.as_view()),
    url(r'^api/set_blocked_multi/(?P<ident>.+)$', views.set_blocked_multi.as_view()),
    url(r'^api/set_unblocked_multi$', views.set_unblocked_multi.as_view()),

    url(r'^api/queue/(?P<ident>.+)', views.BlockQueue.as_view()),
    url(r'^api/unblock_queue/(?P<ident>.+)', views.UnBlockQueue.as_view()),
    url(r'^api/query/(?P<cidr>.+)', views.BlockHistory.as_view()),

    url('^$', browser_views.IndexView.as_view()),
    url('^add$', permission_required('bhr.add_block')(browser_views.AddView.as_view()), name="add"),
    url('^query$', login_required(browser_views.QueryView.as_view()), name="query"),
    url(r'^stats$', browser_views.StatsView.as_view(), name="stats"),
    url(r'^list.csv', views.bhlist, name='csv'),
)
