(function () {
  "use strict";

  const container = document.getElementById("ops-map");
  const markerData = document.getElementById("county-google-markers");
  const status = document.getElementById("ops-map-status");
  if (!container || !markerData || !status) return;

  const key = container.dataset.googleDemoKey;
  if (!key) {
    status.textContent = "Google demo key is missing. Select Free hybrid above.";
    return;
  }

  const reports = JSON.parse(markerData.textContent);
  const riskColors = {
    low: "#2A9D8F", moderate: "#D99B22", high: "#E76F51", critical: "#C83E4D",
  };
  let finished = false;
  const timeout = window.setTimeout(function () {
    if (!finished) fail("Google map timed out. Check your connection or select Free hybrid above.");
  }, 25000);

  function fail(message) {
    if (finished) return;
    finished = true;
    window.clearTimeout(timeout);
    status.textContent = message;
    status.classList.add("text-danger");
  }

  function casePopup(report) {
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = report.ref;
    const details = document.createElement("p");
    details.className = "mb-1";
    details.textContent = report.status + " · " + report.risk + " risk";
    const caseLink = document.createElement("a");
    caseLink.href = report.detail;
    caseLink.textContent = "View case";
    const separator = document.createTextNode(" · ");
    const directions = document.createElement("a");
    directions.href = report.directions;
    directions.textContent = "Directions";
    directions.target = "_blank";
    directions.rel = "noopener noreferrer";
    content.append(title, document.createElement("br"), details, caseLink, separator, directions);
    return content;
  }

  window.gm_authFailure = function () {
    fail("Google rejected the demo key. Check its permissions, then select Free hybrid above.");
  };

  window.initBlueWatchGoogleDemo = async function () {
    try {
      const [{ Map, InfoWindow }, { AdvancedMarkerElement, PinElement }] = await Promise.all([
        google.maps.importLibrary("maps"),
        google.maps.importLibrary("marker"),
      ]);
      if (finished) return;
      const map = new Map(container, {
        center: { lat: -4.04, lng: 39.67 },
        zoom: 9,
        mapId: "DEMO_MAP_ID",
        mapTypeId: "hybrid",
        mapTypeControl: true,
        streetViewControl: false,
        gestureHandling: "cooperative",
      });
      const bounds = new google.maps.LatLngBounds();
      const popup = new InfoWindow();
      let plotted = 0;

      reports.forEach(function (report) {
        const lat = Number(report.lat);
        const lng = Number(report.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
        const position = { lat: lat, lng: lng };
        const pin = new PinElement({
          background: riskColors[report.risk] || "#0077B6",
          borderColor: "#ffffff",
          glyphColor: "#ffffff",
        });
        const marker = new AdvancedMarkerElement({
          map: map,
          position: position,
          title: report.ref + ": " + report.risk + " risk",
          gmpClickable: true,
        });
        marker.append(pin);
        marker.addEventListener("gmp-click", function () {
          popup.setContent(casePopup(report));
          popup.open({ anchor: marker, map: map });
        });
        bounds.extend(position);
        plotted += 1;
      });

      if (plotted > 1) map.fitBounds(bounds, 80);
      else if (plotted === 1) {
        map.setCenter(bounds.getCenter());
        map.setZoom(16);
      }
      finished = true;
      window.clearTimeout(timeout);
      status.textContent = "Google hybrid demo loaded. Map labels come from Google; reports come from BlueWatch.";
    } catch (error) {
      fail("Google map could not load. Check the demo key and browser console, or select Free hybrid above.");
    }
  };

  const script = document.createElement("script");
  script.async = true;
  script.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(key) +
    "&v=weekly&loading=async&callback=initBlueWatchGoogleDemo";
  script.onerror = function () {
    fail("Google map script could not load. Check your connection or select Free hybrid above.");
  };
  document.head.appendChild(script);
})();
