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
    layerGroup(layers) {
      return { layers, addTo(target) { target.layers.add(this); return this; } };
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

test("satellite labels render above imagery and report failed label tiles", () => {
  const tileLayers = [];
  const status = { textContent: "", classList: { toggle() {} } };
  const map = {
    layers: new Set(),
    getZoom() { return 16; },
    on() {},
    hasLayer(layer) { return this.layers.has(layer); },
    removeLayer(layer) { this.layers.delete(layer); },
  };
  const L = {
    tileLayer(url, options) {
      const layer = {
        url, options, handlers: {},
        on(event, callback) { this.handlers[event] = callback; },
        addTo(target) { target.layers.add(this); return this; },
      };
      tileLayers.push(layer);
      return layer;
    },
    layerGroup(layers) {
      return { layers, addTo(target) { target.layers.add(this); return this; } };
    },
    control: {
      layers() { return { addTo() { return this; } }; },
      scale() { return { addTo() { return this; } }; },
    },
  };
  const context = {
    window: { BlueWatchMapConfig: {
      vectorStyleUrl: "", satelliteMaxNativeZoom: 18,
      satelliteLabelUrl: "https://example.invalid/labels/{z}/{x}/{y}",
      satelliteLabelAttribution: "Labels by provider",
    } },
    document: { getElementById() { return status; } },
    L,
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../static/js/maps.js"), "utf8"), context);
  const layers = context.window.BlueWatchMaps.addReliableBaseLayer(map, {
    primaryUrl: "https://example.invalid/street/{z}/{x}/{y}",
    fallbackUrl: "https://example.invalid/satellite/{z}/{x}/{y}",
    initialLayer: "satellite",
    statusElementId: "map-status",
  });

  assert.equal(tileLayers[2].options.zIndex, 2);
  assert.equal(tileLayers[2].options.attribution, "Labels by provider");
  assert.equal(layers.fallback.layers[0], tileLayers[1]);
  assert.equal(layers.fallback.layers[1], tileLayers[2]);
  tileLayers[2].handlers.load();
  assert.match(status.textContent, /Place labels loaded/);
  tileLayers[2].handlers.tileerror();
  assert.match(status.textContent, /place labels are unavailable/);
});
