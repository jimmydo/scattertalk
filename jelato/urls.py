from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'jelato.views.home'),
    (r'^post-office/$', 'jelato.views.post_office'),
    (r'^send-message/$', 'jelato.views.send_message'),
    (r'^contacts/$', 'jelato.views.contacts'),
    (r'^sent/$', 'jelato.views.sent_messages'),
    (r'^subscriptions/$', 'jelato.views.subscriptions'),
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'django.contrib.auth.views.logout'),
    (r'^messages/(?P<message_uuid>\w+)/$', 'jelato.views.message_view'),
    (r'^(?P<username>\w+)/$', 'jelato.views.user_profile'),
    (r'^(?P<username>\w+)/public-messages/(?P<message_uuid>\w+)$', 'jelato.views.public_message_view'),
    (r'^(?P<username>\w+)/feeds/public-messages$', 'jelato.views.public_messages'),
)
