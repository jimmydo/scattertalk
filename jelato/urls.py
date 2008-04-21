from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'jelato.views.home'),
    (r'^post-office/$', 'jelato.views.post_office'),
    (r'^send-message-private/$', 'jelato.views.send_message', { 'is_public': False }),
    (r'^send-message-public/$', 'jelato.views.send_message', { 'is_public': True }),
    (r'^contacts/$', 'jelato.views.contacts'),
    (r'^sent/$', 'jelato.views.sent_messages'),
    (r'^subscriptions/$', 'jelato.views.subscriptions'),
    (r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', 'django.contrib.auth.views.logout'),
    (r'^conversations/(?P<message_uuid>\w+)$', 'jelato.views.conversation_view'),
    (r'^messages/(?P<message_uuid>\w+)/reply$', 'jelato.views.message_reply'),
    (r'^messages/(?P<message_uuid>\w+)/forward$', 'jelato.views.message_forward'),
    (r'^(?P<username>\w+)/$', 'jelato.views.user_profile'),
    (r'^(?P<username>\w+)/public-messages/(?P<message_uuid>\w+)$', 'jelato.views.public_message_view'),
    (r'^(?P<username>\w+)/feeds/public-messages$', 'jelato.views.public_messages'),
)
