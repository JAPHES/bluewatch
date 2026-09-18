(function () {
  "use strict";

  function updateStatus(elementId, message, isError) {
    const element = elementId ? document.getElementById(elementId) : null;
    if (!element) return;
    element.textContent = message;
    element.classList.toggle("text-danger", Boolean(isError));
    element.classList.toggle("text-muted", !isError);
  }

  function addReliableBaseLayer(map, options) {
    const primary = L.tileLayer(options.primaryUrl, {
      maxZoom: 19,
      attribution: options.primaryAttribution,
    });
    const fallback = L.tileLayer(options.fallbackUrl, {
      maxZoom: 19,
      attribution: options.fallbackAttribution,
    });
    let fallbackActive = false;

    primary.once("load", function () {
      updateStatus(options.statusElementId, "Map loaded.", false);
    });
    primary.on("tileerror", function () {
      if (fallbackActive) return;
      fallbackActive = true;
      map.removeLayer(primary);
      fallback.addTo(map);
      updateStatus(options.statusElementId, "Street map unavailable; satellite imagery loaded instead.", false);
    });
    fallback.once("load", function () {
      updateStatus(options.statusElementId, "Satellite map loaded.", false);
    });
    fallback.on("tileerror", function () {
      updateStatus(options.statusElementId, "Map imagery could not be loaded. Check your internet connection.", true);
    });

    primary.addTo(map);
    return { primary: primary, fallback: fallback };
  }

  window.BlueWatchMaps = { addReliableBaseLayer: addReliableBaseLayer };
})();
