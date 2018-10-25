from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Examples:
    # url(r'^$', 'bhr_site.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^bhr/', include('bhr.urls')),
    url(r'^accounts/login/$', auth_views.login, {'template_name': 'login.html'}, name='accounts_login'),
    url(r'^accounts/logout/$', auth_views.logout, name='logout'),

    url(r'^$', RedirectView.as_view(url='/bhr', permanent=False), name='siteroot'),
]
