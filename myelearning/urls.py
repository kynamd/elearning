"""myelearning URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf import settings
from django.views import generic
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from students.views import students, classroom, teachers
from agenda import views as blog_views

from django.views.generic import TemplateView

urlpatterns = [
    url(r'^$', generic.RedirectView.as_view(url='/course/', permanent=True)),
    url(r'^accounts/login/$', auth_views.login, name='login'),
    url(r'^accounts/logout/$', auth_views.logout, name='logout'),
    url(r'^accounts/signup/$', classroom.SignupView.as_view(), name='signup'),
    url(r'^password-change/$', auth_views.password_change, name='password_change'),
    url(r'^password-change/done/$', auth_views.password_change_done, name='password_change_done'),
    url(r'^password-reset/$', auth_views.password_reset, name='password_reset'),
    url(r'^password-reset/done/$', auth_views.password_reset_done, name='password_reset_done'),
    url(r'^password-reset/confirm/(?P<uidb64>[-\w]+)/(?P<token>[-\w]+)/$', auth_views.password_reset_confirm, name='password_reset_confirm'),
    url(r'^password-reset/complete/$', auth_views.password_reset_complete, name='password_reset_complete'),
    url(r'^admin/', admin.site.urls),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^course/', include('courses.urls')),
    url(r'^students/', include('students.urls')),
    url(r'^calendar/', include('agenda.urls')),
    url(r'^api/', include('courses.api.urls', namespace='api')),
    url(r'^api/event/', include('agenda.api.urls', namespace='api_events')),

    url(r'^blog/post/$', blog_views.post_list, name='post_list'),
    url(r'^blog/post/tag/(?P<tag_slug>[-\w]+)/$', blog_views.post_list, name='post_list_by_tag'),
    url(r'^blog/post/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/'\
        r'(?P<post>[-\w]+)/$', blog_views.post_detail, name='post_detail'),
    url(r'^blog/post/(?P<post_id>\d+)/share/$', blog_views.post_share, name='post_share'),
    url(r'^blog/post/like/$', blog_views.post_like, name='post_like'),

    url(r'^sw.js', (TemplateView.as_view(template_name="service-worker.js", content_type='application/javascript', )), name='sw.js'),
    url(r'^offline.html', (TemplateView.as_view(template_name="offline.html")), name='offline.html'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
