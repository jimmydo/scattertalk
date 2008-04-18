from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^statics/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/jimmy/playground/proj1/media' }),
    (r'', include('jelato.urls')),
)
