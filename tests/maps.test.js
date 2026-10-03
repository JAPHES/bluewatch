const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

test("satellite imagery reuses real zoom-18 tiles above native coverage", () => {
  const tileLayers = [];
  const status = { textContent: "", classList: { toggle() {} } };
  const map = {
    zoom: 19,
    handlers: {},
    layers: new Set(),
    getZoom() { return this.zoom; },
    on(event, callback) { this.handlers[event] = callback; },
    hasLayer(layer) { return this.layers.has(layer); },
    removeLayer(layer) { this.layers.delete(layer); },
  };
  const L = {
    tileLayer(url, options) {
      const layer = {
        url,
        options,
        handlers: {},
        on(event, callback) { this.handlers[event] = callback; },
        addTo(target) { target.layers.add(this); return this; },
      };
      tileLayers.push(layer);
      return layer;
    },
    control: {
      layers() { return { addTo() { return this; } }; },
      scale() { return { addTo() { return this; } }; },
    },
  };
  const context = {
    window: { BlueWatchMapConfig: { vectorStyleUrl: "", satelliteMaxNativeZoom: 18 } },
    document: { getElementById() { return status; } },
    L,
  };
  const script = fs.readFileSync(path.join(__dirname, "../static/js/maps.js"), "utf8");
  vm.runInNewContext(script, context);
  context.window.BlueWatchMaps.addReliableBaseLayer(map, {
    primaryUrl: "https://example.invalid/street/{z}/{x}/{y}",
    fallbackUrl: "https://example.invalid/satellite/{z}/{x}/{y}",
    initialLayer: "satellite",
    statusElementId: "map-status",
  });

  assert.equal(tileLayers[1].options.maxNativeZoom, 18);
  assert.equal(tileLayers[1].options.maxZoom, 20);
  map.handlers.zoomend();
  assert.match(status.textContent, /enlarged zoom-18 imagery/);
  map.zoom = 17;
  map.handlers.zoomend();
  assert.equal(status.textContent, "Satellite imagery loaded.");
});
