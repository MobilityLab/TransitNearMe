// Define the Transit namespace.
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
                    'lng': pos.coords.longitude
                });
            },
            function(error) {
                failure && failure(error);
            });
    } else {
        failure && failure();
    }
};

Transit.getIcon = function() {
    var icons = [];
    return function(services) {
        var route_type = -1;
        for (var i in services) {
            route_type = services[i].route.route_type;
        }

        if (!icons[route_type]) {
            switch (route_type.toString()) {
                // Always use the same circle icon.
                default: filename = 'circle.png'; break;
            }
            icons[route_type] = new Transit._leafletMap.TransitIcon('/static/images/' + filename);
        }
        return icons[route_type];
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
    }
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
                maxZoom: 18
            });
    map.doubleClickZoom.disable();
    map.setView(latlng, 15);
    map.addLayer(mqosm);
        
    this.layers = { 'OSM': mqosm };
    this.hiddenLayers = {};
       
    this.segments = {};
    this.stops = {};
    this.routes = {};
    this.services = {};

    this.map = map;
    this.map._wrapper = this; 

    if (options.radius) {
        this.layers['radius'] = new L.Circle(latlng, options.radius, { 
            clickable: false,
            weight: 1,
            fillOpacity: 0.1
        });
    }

    map.on('popupopen', function(e) {
        var src = e.popup._source,
            visibleLayers = {},
            hiddenLayers = [],
            i, j, layer, stop, service, segment, 
            prediction, predictions_str;
   
        if (!src._overlayID) {
            return;
        }
 
        if (src.stop) {
            $.getJSON('/api/stop/' + src.stop.id, function(data) {
                if (data.predictions) {
                    if (e.popup) {
                        predictions_str = '<h2>Wait times</h2>'
                        predictions_str += '<ul class="tnm-stop-prediction-list">';
                        for (i in data.predictions) {
                            prediction = data.predictions[i];
                            predictions_str += '<li>';
                            predictions_str += '<div class="tnm-stop-prediction-route">' + prediction.route + ' ' + prediction.destination + '</div>';
                            predictions_str += '<div class="tnm-stop-prediction-waits"><ul>';
                            for (j in prediction.waits) {
                                predictions_str += '<li>' + prediction.waits[j] + '</li>';
                            }
                            predictions_str += '</ul></div></li>';
                        }

                        if (!data.predictions) {
                            predictions_str += '<li>Wait times unavailable.</li>'
                        }
                        predictions_str += '</ul>';
                        $(e.popup._contentNode).append(predictions_str);
                    }
                }
            });

            visibleLayers[src.stop.layer._leaflet_id] = src.stop.layer;
            for (i in src.stop.services) {
                service = src.stop.services[i];
                for (j in service.segments) {
                    segment = service.segments[j];
                    visibleLayers[segment.layer._leaflet_id] = segment.layer;
                }
            } 
        }
        if (src.segment) {
            visibleLayers[src.segment.layer._leaflet_id] = src.segment.layer;
            for (i in src.segment.services) {
                service = src.segment.services[i];
                visibleLayers[service.stop.layer._leaflet_id] = service.stop.layer;
                for (j in service.segments) {
                    segment = service.segments[j];
                    visibleLayers[segment.layer._leaflet_id] = segment.layer;
                }
            }
        }

        for (i in this._layers)
        {
            layer = this._layers[i];
            if (layer._overlayID && layer._overlayID == src._overlayID) {
                if (!(layer._leaflet_id in visibleLayers)) {
                    hiddenLayers.push(layer);
                }
            }
        }

        for (i in hiddenLayers) {
            this.removeLayer(hiddenLayers[i]);
        }
        this._wrapper.hiddenLayers[src._overlayID] = hiddenLayers;
    });
    map.on('popupclose', function(e) {
        var src = e.popup._source, 
            hiddenLayers, i;

        if (!src._overlayID) {
            return;
        }

        hiddenLayers = this._wrapper.hiddenLayers[src._overlayID];
        for (i in hiddenLayers) {
            this.addLayer(hiddenLayers[i]);
        }
    });
};

Transit._leafletMap.prototype.center = function(latlng) {
    latlng && this.map.setView(latlng, this.map.getZoom());
        this.map.fire('center', { latlng: latlng });
};

Transit._leafletMap.prototype.addCallback = function(options) {
    for (i in options.types) {
        this.map.on(options.types[i], function(e) {
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
                        'lat': e.latlng.lat
                    }),
                    function(data) {
                        options.after && options.after(e, data);
                    });
            } else {
                options.after && options.after(e);
            }
        });
    }
};

Transit._leafletMap.prototype.overlay = function(overlayID, overlay) {
    var oldLayer = this.layers[overlayID],
        layers = new L.LayerGroup(),
        i, j, num;

    oldLayer && this.map.removeLayer(oldLayer);
    delete this.layers[overlayID];
   
    if (!overlay) {
        return;
    }

    this.stops = {};
    this.routes = {};
    this.segments = {};
    this.services = {};

    // Update map containers with new data.
    for (i in overlay.stops) {
        stop = overlay.stops[i];
        stop.services = {};
        this.stops[stop.id] = stop;
    }

    for (i in overlay.routes) {
        route = overlay.routes[i];
        this.routes[route.id] = route;
    }

    for (i in overlay.segments) {
        segment = overlay.segments[i];
        segment.line = Transit.decodePolyline(segment.line_encoded);
        segment.services = {};
        segment.destinations = {};
        this.segments[segment.id] = segment;
    }

    for (i in overlay.services) {
        service = overlay.services[i];
        service.route = this.routes[service.route];
        service.description = service.route.agency + ' ' + service.route.short_name + ' to ' + service.destination;
        
        service.stop = this.stops[service.stop];
        service.stop.services[service.id] = service;

        for (j in service.segments) {
            segment = this.segments[service.segments[j]];
            segment.services[service.id] = service;
            
            if (!(service.route.id in segment.destinations)) {
                segment.destinations[service.route.id] = [];
            }
            segment.destinations[service.route.id].push(service.destination);

            service.segments[j] = segment;
        }

        this.services[service.id] = service;
    }

    // Build segment lines and popups.
    for (i in this.segments) {
        var num_routes = 0, popup_content = '', color;

        segment = this.segments[i];

        for (j in segment.destinations) {
            num_routes++;
        }

        if (num_routes > 1) {
            popup_content += '<ul class="tnm-segment-list">';
        }
        for (j in segment.destinations) {
            route = this.routes[j];
            
            if (num_routes > 1) {
                popup_content += '<li>';
            }
            popup_content += route.agency + ' ' + route.short_name + ' to ' + segment.destinations[route.id].join(', ');
            if (num_routes > 1) {
                popup_content += '</li>';
            }
            
            // A single line can have multiple colors.
            // Pick one arbitrarily. Ideally the line should be dashed,
            // or multiple parallel lines should be shown.
            color = route.color;
        
            // Correct color.
            if (!color) {
                color = '#333333';
            } else {
                color = '#' + color;
            }
        }
        if (num_routes > 1) {
            popup_content += '</ul>';
        }
    
        line = new L.Polyline(segment.line, { color: color, opacity: 0.8 });
        line.segment = segment;
        line.bindPopup(popup_content);
        line._overlayID = overlayID;
        segment.layer = line;
        layers.addLayer(line);
    }
   
    // Build stop icons and popups.
    for (i in this.stops) {
        stop = this.stops[i];

        var icon = Transit.getIcon(stop.services),
            stop_marker = new L.Marker(stop.location, { icon: icon }),
            popup_content = '<h1>' + stop.name + '</h1>',
            num_services = 0;

        for (j in stop.services) {
            num_services++;
        }

        popup_content += '<h2>Services</h2>';
        popup_content += '<ul class="tnm-stop-service-list">';
        for (j in stop.services) {
            popup_content += '<li>';
            popup_content += stop.services[j].description;
            popup_content += '</li>';
        }
        popup_content += '</ul>';
        
        stop_marker.stop = stop;
        stop_marker.bindPopup(popup_content);
        stop_marker._overlayID = overlayID;
        stop.layer = stop_marker;
        layers.addLayer(stop_marker);
    }

    oldLayer && this.map.removeLayer(oldLayer);
    this.layers[overlayID] = layers;
    this.hiddenLayers[overlayID] = [];
    this.map.addLayer(layers);
}

Transit._leafletMap.prototype.radius = function(latlng, radius_m) {
    var radius = this.layers['radius'];    
    if (radius) {
        radius.setLatLng(latlng);
        radius_m && radius.setRadius(radius_m);
        if (!this.map.hasLayer(radius)) {
            this.map.addLayer(radius);
        }
    }
}

Transit._leafletMap.TransitIcon = L.Icon.extend({
    iconUrl: '',
    shadowUrl: '',
    iconSize: new L.Point(25, 25),
    iconAnchor: new L.Point(13, 13),
    popupAnchor: new L.Point(0, 0)
});
