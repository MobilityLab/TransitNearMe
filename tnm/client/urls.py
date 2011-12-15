from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    (r'^$', direct_to_template, {'template': 'client/leaflet.html'}),
    (r'^predictable/$', direct_to_template, {'template': 'client/predictable.html'}),
)
