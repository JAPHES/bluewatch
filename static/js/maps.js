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
    const mapConfig = window.BlueWatchMapConfig || {};
    const satelliteMaxNativeZoom = Number(mapConfig.satelliteMaxNativeZoom) || 18;
    const basicStreet = L.tileLayer(options.primaryUrl, {
      maxZoom: 20,
      attribution: options.primaryAttribution,
    });
    const satellite = L.tileLayer(options.fallbackUrl, {
      maxZoom: 20,
      // Esri can return a 200 OK "Map data not yet available" image at higher zooms.
      maxNativeZoom: satelliteMaxNativeZoom,
      zIndex: 1,
      attribution: options.fallbackAttribution,
    });
    // Reference tiles are transparent: keep labels above imagery and below report markers.
    const labels = mapConfig.satelliteLabelUrl ? L.tileLayer(mapConfig.satelliteLabelUrl, {
      maxZoom: 20,
      maxNativeZoom: satelliteMaxNativeZoom,
      zIndex: 2,
      attribution: mapConfig.satelliteLabelAttribution,
    }) : null;
    const satelliteWithLabels = L.layerGroup(labels ? [satellite, labels] : [satellite]);
    const styleUrl = mapConfig.vectorStyleUrl;
    let street = basicStreet;
    let activeLayer = options.initialLayer === "satellite" || styleUrl || mapConfig.hybridStyleUrl
      ? satelliteWithLabels : basicStreet;
    const failedLayers = new Set();
    let manualSatelliteChoice = false;
    let switchingAutomatically = false;
    let labelsLoaded = false;
    let labelsFailed = false;
    let hybridLoaded = false;

    function satelliteMessage() {
      const imageryMessage = map.getZoom() > satelliteMaxNativeZoom
        ? "Showing enlarged zoom-" + satelliteMaxNativeZoom + " imagery; finer satellite detail is unavailable here."
        : "Satellite imagery loaded.";
      if (hybridLoaded) return imageryMessage + " Roads and local place labels loaded; zoom in for more detail.";
      if (!labels) return imageryMessage;
      if (labelsFailed) return imageryMessage + " Some place labels are unavailable.";
      return imageryMessage + (labelsLoaded ? " Road and place labels loaded." : " Loading road and place labels…");
    }

    const layerControl = L.control.layers(
      { "Streets and roads": basicStreet, "Satellite hybrid": satelliteWithLabels },
      null,
      { position: "topright", collapsed: false },
    ).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);

    activeLayer.addTo(map);

    map.on("baselayerchange", function (event) {
      activeLayer = event.layer;
      if (!switchingAutomatically) manualSatelliteChoice = event.layer === satelliteWithLabels;
      updateStatus(
        options.statusElementId,
        event.layer === satelliteWithLabels ? satelliteMessage() : "Street map selected.",
        false,
      );
    });

    map.on("zoomend", function () {
      if (activeLayer === satelliteWithLabels) updateStatus(options.statusElementId, satelliteMessage(), false);
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
      switchLayer(satelliteWithLabels, "Street map unavailable; " + satelliteMessage());
    });
    satellite.on("load", function () {
      failedLayers.delete(satellite);
      if (map.hasLayer(satelliteWithLabels)) updateStatus(options.statusElementId, satelliteMessage(), false);
    });
    satellite.on("tileerror", function () {
      failedLayers.add(satellite);
      if (activeLayer !== satelliteWithLabels) return;
      if (failedLayers.has(basicStreet)) {
        updateStatus(options.statusElementId, "Map imagery could not be loaded. Check your internet connection.", true);
        return;
      }
      switchLayer(basicStreet, "Satellite imagery unavailable; basic street map loaded instead.");
    });
    if (labels) {
      labels.on("load", function () {
        labelsLoaded = true;
        labelsFailed = false;
        if (map.hasLayer(satelliteWithLabels)) updateStatus(options.statusElementId, satelliteMessage(), false);
      });
      labels.on("tileerror", function () {
        labelsFailed = true;
        if (map.hasLayer(satelliteWithLabels)) updateStatus(options.statusElementId, satelliteMessage(), false);
      });
    }

    if (styleUrl) {
      updateStatus(options.statusElementId, "Loading satellite hybrid map…", false);
      ensureVectorSupport().then(function () {
        if (mapConfig.hybridStyleUrl) {
          // The transparent OSM style adds roads and named local POIs. Keep the
          // Esri reference layer in place until this optional detail actually loads.
          const paneName = "bluewatch-hybrid-labels";
          if (!map.getPane(paneName)) {
            const pane = map.createPane(paneName);
            pane.style.zIndex = "250"; // Above imagery tiles, below report markers.
            pane.style.pointerEvents = "none";
          }
          const hybrid = L.maplibreGL({
            style: mapConfig.hybridStyleUrl,
            attribution: vectorAttribution,
            attributionControl: false,
            interactive: false,
            canvasContextAttributes: { alpha: true },
            pane: paneName,
          });
          hybrid.on("add", function () {
            const hybridMap = hybrid.getMaplibreMap();
            if (!hybridMap) return;
            let settled = false;
            // Wait until requested vector tiles and glyphs settle before
            // removing the raster reference layer beneath them.
            hybridMap.once("idle", function () {
              settled = true;
              hybridLoaded = true;
              if (labels) satelliteWithLabels.removeLayer(labels);
              if (map.hasLayer(satelliteWithLabels)) updateStatus(options.statusElementId, satelliteMessage(), false);
            });
            hybridMap.once("error", function () {
              if (settled) return;
              settled = true;
              satelliteWithLabels.removeLayer(hybrid);
              if (map.hasLayer(satelliteWithLabels)) updateStatus(options.statusElementId, satelliteMessage(), false);
            });
          });
          satelliteWithLabels.addLayer(hybrid);
        }
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
            if (!loaded && map.hasLayer(detailedStreet)) switchLayer(satelliteWithLabels, "Detailed street map unavailable; " + satelliteMessage());
          });
        });
        if (activeLayer === basicStreet || (options.initialLayer === "street" && !manualSatelliteChoice)) {
          switchLayer(detailedStreet, "Loading detailed street map…");
        }
      }).catch(function () {
        if (activeLayer === satelliteWithLabels) {
          updateStatus(options.statusElementId, "OpenStreetMap detail unavailable; " + satelliteMessage(), false);
        }
      });
    }

    return { primary: street, fallback: satelliteWithLabels };
  }

  window.BlueWatchMaps = { addReliableBaseLayer: addReliableBaseLayer };
})();
