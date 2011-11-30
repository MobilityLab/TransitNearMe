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

Transit.getIcon = function() {
    var icons = [];
    return function(routeTypes) {
        if (1 != routeTypes.length) {
            var routeType = -1; 
        } else {
            var routeType = routeTypes[0];
        }

        if (!icons[routeType]) {
            switch (routeType) {
                case 0: filename = '23_bus_inv_thumb.gif'; break;
                case 1: filename = '25_railtransportation_inv_thumb.gif'; break;
                case 2: filename = '25_railtransportation_inv_thumb.gif'; break;
                case 3: filename = '23_bus_inv_thumb.gif'; break;
                default: filename = 'marker.png'; break;
            }
            icons[routeType] = new Transit._leafletMap.TransitIcon('/static/images/' + filename);
        }
        return icons[routeType];
    };
}();

Transit.decodePolyline = function(polyline) {
    var coords = [],
        i = 0,    
        lat = 0,
        lng = 0;

    while (i < polyline.length) {
        var ch, 
            num = 0;
            shift = 0;
        do {
            ch = polyline.charCodeAt(i++) - 63;
            num |= (ch & 0x1f) << shift;
            shift += 5;
        } while (ch >= 0x20);

        if (num & 1 > 0) {
            num = ~num;
        }
        num = num >> 1;
        lat += num * 1e-5;
    
        shift = 0;
        num = 0;
        do {
            ch = polyline.charCodeAt(i++) - 63;
            num |= (ch & 0x1f) << shift;
            shift += 5;
        } while( ch >= 0x20);
        
        if (num & 1 > 0) {
            num = ~num;
        }
        num = num >> 1;
        lng += num * 1e-5;        
        
        coords.push(new L.LatLng(lat, lng))
    }

    return coords;
}

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
		var src = e.popup._source;
        this._hiddenLayers = [];
		for (lid in this._layers)
		{
			var layer = this._layers[lid];

            if (src.stop) {
                if ((layer.stop && src.stop != layer.stop) ||
                    (layer.service && -1 == $.inArray(layer.service, src.stop.services))) {
                    this._hiddenLayers.push(layer);
                    this.removeLayer(layer);
                }
            }
            if (src.service) {
                if ((layer.service && src.service != layer.service) ||
                    (layer.stop && -1 == $.inArray(src.service, layer.stop.services))) {
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
				options.after && options.after(e);
			}
		});
	}
};

Transit._leafletMap.prototype.overlay = function(overlayID, overlay) {
	var oldLayer = this._layers[overlayID];
    oldLayer && this._map.removeLayer(oldLayer);
    delete this._layers[overlayID];
   
    if (!overlay) {
        return;
    }

    var layerGroup = new L.LayerGroup(),
        services = overlay.services,
        stops = overlay.stops,
        routes = overlay.routes;
 
    for (var i in services) {
        var service = services[i],
            stop = stops[service.stop],
            route = routes[service.route];
        
        if (!stop.services) {
            stop.services = [];
        }
        stop.services.push(service);

        if (!stop.service_types) {
            stop.service_types = [];
        }
        if (-1 == $.inArray(route.route_type, stop.service_types)) {
            stop.service_types.push(route.route_type);
        }

        if (!stop.routes) {
            stop.routes = [];
        }
        if (-1 == $.inArray(route, stop.routes)) {
            stop.routes.push(route);
        }
    }
    
    for (var stop_id in stops) {
        stop = stops[stop_id];
        var icon = Transit.getIcon(stop.service_types),
            stop_marker = new L.Marker(stop.location, { icon: icon });
        stop_marker.stop = stop;

        var popup_content = '<p>' + stop.name + '</p><ul>';
        for (var i in stop.services) {
            var service = stop.services[i]; 
            popup_content += '<li>' + routes[service.route].agency + ' ' + routes[service.route].short_name + ' to ' + service.destination + '</li>';
        }
        popup_content += '</ul>';
        stop_marker.bindPopup(popup_content);
        layerGroup.addLayer(stop_marker); 
    }

    for (var stop_id in stops) {
        stop = stops[stop_id];
        for (var i in stop.services) {
            var service = stop.services[i],
                color = routes[service.route].color;
            if (!color) {
                color = '#333333';
            }
            for (var j in service.segments) {
                var segment = service.segments[j],
                    latlngs = Transit.decodePolyline(segment.points);
                    service_line = new L.Polyline(latlngs, { color: color, opacity: 0.8 });
                service_line.service = service;

                var popup_content = routes[service.route].agency + ' ' + routes[service.route].short_name + ' to ' + service.destination;
                service_line.bindPopup(popup_content);
                layerGroup.addLayer(service_line);
            }
        }
    }

    oldLayer && this._map.removeLayer(oldLayer);
    this._layers[overlayID] = layerGroup;
    this._map.addLayer(layerGroup);
    this._map._services = services;
    this._map._stops = stops;
    this._map._routes = routes;
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
