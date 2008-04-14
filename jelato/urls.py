from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'jelato.views.home'),
    (r'^post-office/$', 'jelato.views.post_office'),
    (r'^send-message/$', 'jelato.views.send_message'),
    (r'^sent/$', 'jelato.views.sent_messages'),
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'django.contrib.auth.views.logout'),
    (r'^(?P<username>\w+)/public-messages/$', 'jelato.views.public_messages'),
    (r'^(?P<username>\w+)/$', 'jelato.views.user_profile'),
)
