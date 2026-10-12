/*
 * script.js — Image2PSD tool logic.
 * Loads an image in the browser, shows a preview with optional auto
 * corrections, and exports a real PSD file via psd-encoder.js.
 * Everything runs locally in the browser; no files leave the device.
 */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };

  var state = {
    source: null,        // ImageBitmap or HTMLImageElement of the source file
    sourceName: '',
    adjustedCanvas: null // offscreen canvas holding the corrected image
  };

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    $('convert-button').addEventListener('click', onConvert);
    $('export-button').addEventListener('click', onExport);
    $('image-input').addEventListener('change', function () {
      $('convert-button').disabled = !$('image-input').files.length;
    });
    // Rebuild the preview whenever a correction option changes.
    var options = document.querySelectorAll('#auto-correction-options input, #auto-correction-options select');
    for (var i = 0; i < options.length; i++) {
      options[i].addEventListener('change', refreshPreview);
      options[i].addEventListener('input', refreshPreview);
    }
    $('convert-button').disabled = true;
    $('export-button').disabled = true;
  }

  function setStatus(message, isError) {
    var el = $('status');
    el.textContent = message || '';
    el.className = isError ? 'error' : '';
  }

  function readOptions() {
    return {
      autoContrast: $('opt-auto-contrast').checked,
      grayscale: $('opt-grayscale').checked,
      trimTransparent: $('opt-trim-transparent').checked,
      background: $('opt-background').value,
      maxDimension: parseInt($('opt-max-dimension').value, 10) || 0
    };
  }

  function onConvert() {
    var file = $('image-input').files[0];
    if (!file) {
      setStatus('Choose an image file first.', true);
      return;
    }
    setStatus('Loading image…');
    state.sourceName = file.name.replace(/\.[^.]+$/, '') || 'image';
    var url = URL.createObjectURL(file);
    var done = function (source) {
      state.source = source;
      URL.revokeObjectURL(url);
      refreshPreview();
      renderInfo(source.width, source.height);
      $('export-button').disabled = false;
      setStatus('Ready. Adjust the options, then export.');
    };
    var fail = function () {
      URL.revokeObjectURL(url);
      setStatus('Could not decode that file as an image.', true);
    };
    if (typeof createImageBitmap === 'function') {
      createImageBitmap(file).then(done, function () { loadViaImage(url, done, fail); });
    } else {
      loadViaImage(url, done, fail);
    }
  }

  function loadViaImage(url, done, fail) {
    var img = new Image();
    img.onload = function () { done(img); };
    img.onerror = fail;
    img.src = url;
  }

  /* Draw the source onto a canvas, applying the chosen corrections, and
   * return { canvas, trimmed } where trimmed is the tight content rect. */
  function buildAdjustedCanvas() {
    var opts = readOptions();
    var src = state.source;
    var width = src.width;
    var height = src.height;

    // Optional downscale to stay within the PSD version 1 size limits.
    if (opts.maxDimension > 0 && Math.max(width, height) > opts.maxDimension) {
      var scale = opts.maxDimension / Math.max(width, height);
      width = Math.max(1, Math.round(width * scale));
      height = Math.max(1, Math.round(height * scale));
    }

    var canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    var ctx = canvas.getContext('2d');

    var hasAlpha = true;
    if (opts.background !== 'keep') {
      ctx.fillStyle = opts.background;
      ctx.fillRect(0, 0, width, height);
      hasAlpha = false;
    }
    ctx.drawImage(src, 0, 0, width, height);

    var imageData = ctx.getImageData(0, 0, width, height);
    var d = imageData.data;
    if (opts.grayscale) {
      for (var i = 0; i < d.length; i += 4) {
        var g = Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
        d[i] = d[i + 1] = d[i + 2] = g;
      }
    }
    if (opts.autoContrast) {
      applyAutoContrast(d);
    }
    if (opts.grayscale || opts.autoContrast) {
      ctx.putImageData(imageData, 0, 0);
    }
    return { canvas: canvas, hasAlpha: hasAlpha };
  }

  /* Simple percentile-stretch auto contrast per RGB channel. */
  function applyAutoContrast(d) {
    var hist = [new Uint32Array(256), new Uint32Array(256), new Uint32Array(256)];
    var i, count = d.length / 4;
    for (i = 0; i < d.length; i += 4) {
      hist[0][d[i]]++;
      hist[1][d[i + 1]]++;
      hist[2][d[i + 2]]++;
    }
    var cutoff = Math.floor(count * 0.005);
    var maps = [];
    for (var c = 0; c < 3; c++) {
      var lo = 0, hi = 255, acc = 0;
      while (lo < 255 && acc + hist[c][lo] <= cutoff) { acc += hist[c][lo]; lo++; }
      acc = 0;
      while (hi > 0 && acc + hist[c][hi] <= cutoff) { acc += hist[c][hi]; hi--; }
      var map = new Uint8Array(256);
      var range = Math.max(1, hi - lo);
      for (var v = 0; v < 256; v++) {
        map[v] = v <= lo ? 0 : v >= hi ? 255 : Math.round(((v - lo) * 255) / range);
      }
      maps.push(map);
    }
    for (i = 0; i < d.length; i += 4) {
      d[i] = maps[0][d[i]];
      d[i + 1] = maps[1][d[i + 1]];
      d[i + 2] = maps[2][d[i + 2]];
    }
  }

  /* Find the bounding box of non-transparent pixels. */
  function findContentBounds(ctx, width, height) {
    var d = ctx.getImageData(0, 0, width, height).data;
    var top = -1, left = -1, bottom = -1, right = -1;
    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        if (d[(y * width + x) * 4 + 3] !== 0) {
          if (top === -1) top = y;
          bottom = y;
          if (left === -1 || x < left) left = x;
          if (x > right) right = x;
        }
      }
    }
    if (top === -1) return null; // fully transparent
    return { top: top, left: left, width: right - left + 1, height: bottom - top + 1 };
  }

  function refreshPreview() {
    if (!state.source) return;
    var result = buildAdjustedCanvas();
    state.adjustedCanvas = result.canvas;
    var preview = $('preview-canvas');
    var maxW = preview.parentElement.clientWidth || 600;
    var scale = Math.min(1, maxW / result.canvas.width, 400 / result.canvas.height);
    preview.width = Math.max(1, Math.round(result.canvas.width * scale));
    preview.height = Math.max(1, Math.round(result.canvas.height * scale));
    var pctx = preview.getContext('2d');
    pctx.clearRect(0, 0, preview.width, preview.height);
    pctx.drawImage(result.canvas, 0, 0, preview.width, preview.height);
    renderInfo(result.canvas.width, result.canvas.height);
  }

  function renderInfo(width, height) {
    $('image-info').textContent = 'Output size: ' + width + ' × ' + height + ' px';
  }

  function onExport() {
    if (!state.adjustedCanvas) {
      setStatus('Convert an image first.', true);
      return;
    }
    setStatus('Encoding PSD…');
    // Defer so the status text paints before the (blocking) encode.
    setTimeout(function () {
      try {
        var psdBytes = encodeCurrentCanvas();
        download(psdBytes, state.sourceName + '.psd');
        setStatus('Done — saved ' + state.sourceName + '.psd (' +
          (psdBytes.length / 1024).toFixed(1) + ' KB).');
      } catch (err) {
        setStatus('Export failed: ' + err.message, true);
      }
    }, 20);
  }

  function encodeCurrentCanvas() {
    var opts = readOptions();
    var canvas = state.adjustedCanvas;
    var ctx = canvas.getContext('2d');
    var width = canvas.width;
    var height = canvas.height;
    var bounds = { top: 0, left: 0, width: width, height: height };
    if (opts.trimTransparent) {
      var found = findContentBounds(ctx, width, height);
      if (found) bounds = found;
    }
    var planes = extractPlanes(ctx, bounds.left, bounds.top, bounds.width, bounds.height);
    return PsdEncoder.encode({
      width: width,
      height: height,
      composite: planes,
      layers: [{
        name: state.sourceName || 'Layer 1',
        top: bounds.top,
        left: bounds.left,
        width: bounds.width,
        height: bounds.height,
        r: planes.r,
        g: planes.g,
        b: planes.b,
        a: planes.a
      }]
    });
  }

  /* Split canvas RGBA pixels into per-channel Uint8Array planes. */
  function extractPlanes(ctx, x, y, width, height) {
    var data = ctx.getImageData(x, y, width, height).data;
    var size = width * height;
    var r = new Uint8Array(size);
    var g = new Uint8Array(size);
    var b = new Uint8Array(size);
    var a = new Uint8Array(size);
    var opaque = true;
    for (var i = 0, p = 0; i < data.length; i += 4, p++) {
      r[p] = data[i];
      g[p] = data[i + 1];
      b[p] = data[i + 2];
      a[p] = data[i + 3];
      if (data[i + 3] !== 255) opaque = false;
    }
    return { r: r, g: g, b: b, a: opaque ? null : a };
  }

  function download(bytes, filename) {
    var blob = new Blob([bytes], { type: 'image/vnd.adobe.photoshop' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
})();
