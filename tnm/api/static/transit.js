(function(x) {
	x.Transit = {};
})(this);

// Common library functions.
Transit.addMap = function(type, element, options) {
	switch(type)
	{
		case 'Leaflet': return new Transit._leafletMap(element, options);
		default: throw 'Unknown map type.';
	};
};

Transit.tryGeolocating = function(success, failure) {
	if (navigator && navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(
			function(pos) {
				success && success({
					'lat': pos.coords.latitude,
					'lng': pos.coords.longitude,
				});
			},
			function(error) {
				failure && failure(error);
			}
		);
	}
};

// API calls.
Transit.API = {
	_call: function(urlTmpl) {
		return function(params, callback) {
			var url = urlTmpl, d;
			for (i in params) {
				if ($.isFunction(params[i])) {
					params[i] = params[i]();
				}
				url = url.replace(RegExp('\\{'+i+'\\}', 'gi'), params[i]);
			}
			d = $.getJSON(url);
			callback && d.success(callback);
		};
	},
};

Transit.API.getNearby = Transit.API._call(
	'/api/nearby?lng={lng}&lat={lat}&radius_m={radius_m}');

// Leaflet Map wrapper.
Transit._leafletMap = function(element, options) {
	var map = new L.Map(element, { attributionControl: false }),
		latlng = new L.LatLng(options.lat, options.lng),
		url = 'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
		mqosm = new L.TileLayer(
			url,
			{
				subdomains: '1234',
				maxZoom: 18,
			}
		);
	map.doubleClickZoom.disable();
	map.setView(latlng, 15);
	map.addLayer(mqosm);
	
	this._map = map;
	this._layers = { 'OSM': mqosm };
	this._geolayers = {};

	if (options.radius) {
		this._layers['radius'] = new L.Circle(latlng, options.radius, { 
			clickable: false,
			weight: 1,
			fillOpacity: 0.1, 
		});
	}

	map.on('popupopen', function(e) {
		if (!e.popup._source || !e.popup._source.featureProperties) {
			return
		}
		
		var props = e.popup._source.featureProperties;
		this._hiddenLayers = [];
		for (lid in this._layers)
		{
			var layer = this._layers[lid];

			if (props.stops && layer.featureProperties) {
				if ((layer.featureProperties.pattern && layer.featureProperties.pattern != props.pattern) ||
					(layer.featureProperties.stop && -1 == $.inArray(layer.featureProperties.stop, props.stops))) {
					this._hiddenLayers.push(layer);
					this.removeLayer(layer);
				}
			}
			if (props.patterns && layer.featureProperties) {
				if ((layer.featureProperties.stop && layer.featureProperties.stop != props.stop) ||
					(layer.featureProperties.pattern && -1 == $.inArray(layer.featureProperties.pattern, props.patterns))) {
					this._hiddenLayers.push(layer);
					this.removeLayer(layer);
				}
			}
		}
	});
	map.on('popupclose', function(e) {
		if (this._hiddenLayers) {
			for (rl in this._hiddenLayers) {
				this.addLayer(this._hiddenLayers[rl]);
			}
		}
	});
};

Transit._leafletMap.prototype.center = function(latlng) {
	latlng && this._map.setView(latlng, this._map.getZoom());
	this._map.fire('center', { latlng: this._map.getCenter() });
};

Transit._leafletMap.prototype.addCallback = function(options) {
	for (i in options.types) {
		this._map.on(options.types[i], function(e) {
			if (!e.latlng) {
				e.latlng = e.target.getCenter();
			}
			options.before && options.before(e);
			if (options.apiCall) {
				options.apiCall($.extend(
					{}, 
					options.extraParams, 
					{
						'lng': e.latlng.lng,
						'lat': e.latlng.lat,
					}),
					function(data) {
						options.after && options.after(e, data);
					}
				);
			} else {
				options.after(e);
			}
		});
	}
};

Transit._leafletMap.prototype.overlay = function(overlay, overlayID) {
	var oldLayer = this._layers[overlayID],
		geoLayer = new L.GeoJSON(),
		stopLayers = [],
		patternLayers = [];
	
	geoLayer.on('featureparse', function(e) {
		if (e.layer.setIcon && e.properties && e.properties.route_types) {
			var icon;
			switch (e.properties.route_types[0]) {
				case 0: icon = '23_bus_inv_thumb.gif'; break;
				case 1: icon = '25_railtransportation_inv_thumb.gif'; break;
				case 2: icon = '25_railtransportation_inv_thumb.gif'; break;
				case 3: icon = '23_bus_inv_thumb.gif'; break;
				default: break;
			}
			icon && e.layer.setIcon(new Transit._leafletMap.TransitIcon(
				'/static/images/' + icon));
		}
		if (e.properties && e.properties.name) {
			if (e.properties.route_names) {
				e.layer.bindPopup(e.properties.name + ' (' + e.properties.route_names.join(', ') + ')');
			} else if (e.properties.name) {
				if (e.properties.destination) {
					e.layer.bindPopup(e.properties.name + ' to ' + e.properties.destination);
				} else {
					e.layer.bindPopup(e.properties.name);
				}
			}
		}
		if (e.properties && e.layer.setStyle) {
			if (e.properties.color) {
				e.layer.setStyle({'color': '#' + e.properties.color});
			} else {
				e.layer.setStyle({'color': '#333333'});
			}
		}

		if (!e.layer.featureProperties) {
			e.layer.featureProperties = {};
		}
		if (e.properties && e.properties.stops) {
			e.layer.featureProperties.stops = e.properties.stops;
			e.layer.featureProperties.pattern = e.properties.id;
			patternLayers.push(e.properties.id);			
		}
		if (e.properties && e.properties.patterns) {
			e.layer.featureProperties.patterns = e.properties.patterns;
			e.layer.featureProperties.stop = e.properties.id;
			stopLayers.push(e.properties.id);			
		}
	});

	geoLayer.addGeoJSON(overlay);

	this._layers[overlayID] = geoLayer;
	this._map.addLayer(geoLayer);
	oldLayer && this._map.removeLayer(oldLayer);

	this._stopLayers = stopLayers;
	this._patternLayers = patternLayers;
}

Transit._leafletMap.prototype.radius = function(latlng, radius_m) {
	var radius = this._layers['radius'];	
	if (radius) {
		radius.setLatLng(latlng);
		radius_m && radius.setRadius(radius_m);
		if (!this._map.hasLayer(radius)) {
			this._map.addLayer(radius);
		}
	}
}

Transit._leafletMap.TransitIcon = L.Icon.extend({
	iconUrl: '',
	shadowUrl: '',
	iconSize: new L.Point(25, 25),
	iconAnchor: new L.Point(13, 13),
	popupAnchor: new L.Point(0, -7),
});
