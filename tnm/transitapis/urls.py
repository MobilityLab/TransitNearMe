from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('transitapis.views',
    (r'^$', direct_to_template, {'template': 'transitapis/predictions.html'}),
    url(r'^stops', 'stops', name='stops'),
    url(r'^predictions', 'predictions', name='predictions'),
)
