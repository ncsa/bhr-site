from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import include, url

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

urlpatterns = [
    # Examples:
    # url(r'^$', 'testapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^api/', include(router.urls)),
    url(r'^api/block$', views.block.as_view()),
    url(r'^api/unblock_now$', views.unblock_now.as_view()),
    url(r'^api/stats$', views.stats),
    url(r'^api/metrics$', views.metrics),
    url(r'^api/source_stats$', views.source_stats),

    url(r'^api/mblock$', views.mblock.as_view()),
    url(r'^api/set_blocked_multi/(?P<ident>.+)$', views.set_blocked_multi.as_view()),
    url(r'^api/set_unblocked_multi$', views.set_unblocked_multi.as_view()),

    url(r'^api/queue/(?P<ident>.+)', views.BlockQueue.as_view()),
    url(r'^api/unblock_queue/(?P<ident>.+)', views.UnBlockQueue.as_view()),
    url(r'^api/query/(?P<cidr>.+)', views.BlockHistory.as_view()),

    url('^$', browser_views.IndexView.as_view(), name="home"),
    url('^add$', permission_required('bhr.add_block', raise_exception=True)(browser_views.AddView.as_view()), name="add"),
    url('^query$', login_required(browser_views.QueryView.as_view()), name="query"),
    url('^unblock$', permission_required('bhr.change_block', raise_exception=True)(browser_views.UnblockView.as_view()), name="unblock"),
    url('^do_unblock$', permission_required('bhr.change_block', raise_exception=True)(browser_views.DoUnblockView.as_view()), name="do_unblock"),
    url(r'^stats$', browser_views.StatsView.as_view(), name="stats"),
    url(r'^list$', login_required(browser_views.ListView.as_view()), name="list"),
    url(r'^list/source/(?P<source>.+)$', login_required(browser_views.SourceListView.as_view()), name="source-list"),
    url(r'^list.csv', views.bhlist.as_view(), name='csv'),

    # auth mechanism agnostic login
    url(r'^login$', browser_views.login, name='login'),
]

if settings.BHR.get('unauthenticated_limited_query', False):
    urlpatterns.extend([
        url(r'^publist.csv', views.bhlistpub, name='pubcsv'),

        url(r'^api/query_limited/(?P<cidr>.+)', views.BlockHistoryLimited.as_view()),
        url('^limited/query$', browser_views.QueryViewLimited.as_view(), name="query_limited"),
        url('^limited/list$', browser_views.ListViewLimited.as_view(), name="list_limited"),
    ])
else:
    urlpatterns.extend([
        url(r'^publist.csv', login_required(views.bhlistpub), name='pubcsv'),
    ])
