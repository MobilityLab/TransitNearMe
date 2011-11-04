from django.conf.urls.defaults import patterns, include, url
from api.views import *

urlpatterns = patterns('api.views',
	(r'^stops$', NearbyStopsView.as_view()),
	(r'^routes$', NearbyRoutesView.as_view()),
	(r'^nearby$', NearbyView.as_view()),
)
