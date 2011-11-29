from django.conf.urls.defaults import patterns, include, url
from api.views import *

urlpatterns = patterns('api.views',
    url(r'stop/(?P<id>\d+)$', StopView.as_view(), name='stop'),
    url(r'stops$', NearbyStopsView.as_view(), name='stops'),
    url(r'nearby$', NearbyView.as_view(), name='nearby'),
)
