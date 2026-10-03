(function () {
  "use strict";

  const vectorAttribution = 'OpenFreeMap &copy; OpenMapTiles Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';
  const mapLibreUrl = "https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.1/dist/maplibre-gl.js";
  const leafletAdapterUrl = "https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js";
  let vectorSupportPromise;

  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      const script = document.createElement("script");
      script.src = url;
      script.onload = resolve;
      script.onerror = function () { reject(new Error("Map library could not be loaded.")); };
      document.head.appendChild(script);
    });
  }

  function ensureVectorSupport() {
    if (typeof L.maplibreGL === "function") return Promise.resolve();
    if (!vectorSupportPromise) {
      vectorSupportPromise = Promise.resolve()
        .then(function () { return window.maplibregl ? null : loadScript(mapLibreUrl); })
        .then(function () { return loadScript(leafletAdapterUrl); })
        .then(function () {
          if (typeof L.maplibreGL !== "function" || !window.maplibregl || !maplibregl.supported()) {
            throw new Error("Detailed street maps are unavailable in this browser.");
          }
        });
    }
    return vectorSupportPromise;
  }

  function updateStatus(elementId, message, isError) {
    const element = elementId ? document.getElementById(elementId) : null;
    if (!element) return;
    element.textContent = message;
    element.classList.toggle("text-danger", Boolean(isError));
    element.classList.toggle("text-muted", !isError);
  }

  function addReliableBaseLayer(map, options) {
    const basicStreet = L.tileLayer(options.primaryUrl, {
      maxZoom: 19,
      attribution: options.primaryAttribution,
    });
    const satellite = L.tileLayer(options.fallbackUrl, {
      maxZoom: 19,
      attribution: options.fallbackAttribution,
    });
    const styleUrl = (window.BlueWatchMapConfig || {}).vectorStyleUrl;
    let street = basicStreet;
    let activeLayer = options.initialLayer === "satellite" || styleUrl ? satellite : basicStreet;
    const failedLayers = new Set();
    let manualSatelliteChoice = false;
    let switchingAutomatically = false;

    const layerControl = L.control.layers(
      { "Streets and roads": basicStreet, "Satellite imagery": satellite },
      null,
      { position: "topright", collapsed: false },
    ).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);

    activeLayer.addTo(map);

    map.on("baselayerchange", function (event) {
      activeLayer = event.layer;
      if (!switchingAutomatically) manualSatelliteChoice = event.layer === satellite;
      updateStatus(
        options.statusElementId,
        event.layer === satellite ? "Satellite imagery selected." : "Street map selected.",
        false,
      );
    });

    function switchLayer(next, message) {
      switchingAutomatically = true;
      if (map.hasLayer(activeLayer)) map.removeLayer(activeLayer);
      next.addTo(map);
      activeLayer = next;
      switchingAutomatically = false;
      updateStatus(options.statusElementId, message, false);
    }

    basicStreet.on("load", function () {
      failedLayers.delete(basicStreet);
      if (map.hasLayer(basicStreet)) updateStatus(options.statusElementId, "Street map loaded.", false);
    });
    basicStreet.on("tileerror", function () {
      failedLayers.add(basicStreet);
      if (activeLayer !== basicStreet) return;
      if (failedLayers.has(satellite)) {
        updateStatus(options.statusElementId, "Map imagery could not be loaded. Check your internet connection.", true);
        return;
      }
      switchLayer(satellite, "Street map unavailable; satellite imagery loaded instead.");
    });
    satellite.on("load", function () {
      failedLayers.delete(satellite);
      if (map.hasLayer(satellite)) updateStatus(options.statusElementId, "Satellite imagery loaded.", false);
    });
    satellite.on("tileerror", function () {
      failedLayers.add(satellite);
      if (activeLayer !== satellite) return;
      if (failedLayers.has(basicStreet)) {
        updateStatus(options.statusElementId, "Map imagery could not be loaded. Check your internet connection.", true);
        return;
      }
      switchLayer(basicStreet, "Satellite imagery unavailable; basic street map loaded instead.");
    });

    if (styleUrl) {
      updateStatus(options.statusElementId, "Loading detailed street map…", false);
      ensureVectorSupport().then(function () {
        const detailedStreet = L.maplibreGL({
          style: styleUrl,
          attribution: vectorAttribution,
          attributionControl: false,
        });
        street = detailedStreet;
        layerControl.removeLayer(basicStreet);
        layerControl.addBaseLayer(detailedStreet, "Streets and roads");
        detailedStreet.on("add", function () {
          const vectorMap = detailedStreet.getMaplibreMap();
          if (!vectorMap) return;
          let loaded = false;
          vectorMap.once("load", function () {
            loaded = true;
            if (map.hasLayer(detailedStreet)) updateStatus(options.statusElementId, "Detailed street map loaded.", false);
          });
          vectorMap.once("error", function () {
            if (!loaded && map.hasLayer(detailedStreet)) switchLayer(satellite, "Detailed street map unavailable; satellite imagery loaded instead.");
          });
        });
        if (options.initialLayer !== "satellite" && !manualSatelliteChoice) {
          switchLayer(detailedStreet, "Loading detailed street map…");
        }
      }).catch(function () {
        if (activeLayer === satellite) {
          updateStatus(options.statusElementId, "Detailed street map unavailable; satellite imagery loaded.", false);
        }
      });
    }

    return { primary: street, fallback: satellite };
  }

  window.BlueWatchMaps = { addReliableBaseLayer: addReliableBaseLayer };
})();
