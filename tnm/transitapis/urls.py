from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('transitapis.views',
    url(r'^api/predictable', 'predictable', name='predictable'),
    url(r'^api/predictions', 'predictions', name='predictions'),
)
