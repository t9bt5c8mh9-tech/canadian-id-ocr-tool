/*
 * psd-encoder.js — dependency-free PSD (Photoshop) file writer.
 *
 * Writes PSD version 1 files: 8-bit RGB/RGBA, PackBits (RLE) compressed
 * channels, a flattened composite image plus optional raster layers.
 * Exposes a single global: PsdEncoder.encode(options) -> Uint8Array.
 *
 * options = {
 *   width, height,                  // canvas size in pixels (1..30000)
 *   composite: { r, g, b, a? },     // full-size Uint8Array planes (w*h each)
 *   layers: [ {                     // optional, ordered bottom-to-top
 *     name, top, left, width, height,
 *     r, g, b, a?                   // Uint8Array planes for the layer rect
 *   } ]
 * }
 */
(function (global) {
  'use strict';

  var MAX_DIMENSION = 30000; // PSD version 1 limit

  function ByteWriter() {
    this.parts = [];
    this.length = 0;
  }
  ByteWriter.prototype.u8 = function (v) {
    this.bytes([v & 0xff]);
  };
  ByteWriter.prototype.u16 = function (v) {
    this.bytes([(v >> 8) & 0xff, v & 0xff]);
  };
  ByteWriter.prototype.i16 = function (v) {
    this.u16(v & 0xffff);
  };
  ByteWriter.prototype.u32 = function (v) {
    this.bytes([(v >>> 24) & 0xff, (v >>> 16) & 0xff, (v >>> 8) & 0xff, v & 0xff]);
  };
  ByteWriter.prototype.i32 = function (v) {
    this.u32(v >>> 0);
  };
  ByteWriter.prototype.ascii = function (s) {
    for (var i = 0; i < s.length; i++) this.u8(s.charCodeAt(i));
  };
  ByteWriter.prototype.bytes = function (arr) {
    var u8 = arr instanceof Uint8Array ? arr : Uint8Array.from(arr);
    this.parts.push(u8);
    this.length += u8.length;
  };
  ByteWriter.prototype.concat = function () {
    var out = new Uint8Array(this.length);
    var offset = 0;
    for (var i = 0; i < this.parts.length; i++) {
      out.set(this.parts[i], offset);
      offset += this.parts[i].length;
    }
    return out;
  };

  /* PackBits-compress a single row of pixel data. */
  function packBitsRow(row) {
    var out = [];
    var n = row.length;
    var i = 0;
    while (i < n) {
      var run = 1;
      while (i + run < n && row[i + run] === row[i] && run < 128) run++;
      if (run >= 3) {
        out.push(257 - run, row[i]);
        i += run;
        continue;
      }
      var start = i;
      i += run;
      while (i < n) {
        var r = 1;
        while (i + r < n && row[i + r] === row[i] && r < 128) r++;
        if (r >= 3 || i - start >= 128) break;
        i += r;
      }
      out.push(i - start - 1);
      for (var k = start; k < i; k++) out.push(row[k]);
    }
    return Uint8Array.from(out);
  }

  /* Build a "channel image data" block: u16 compression=1 (RLE), per-row
   * u16 byte counts for every channel, then the PackBits data. */
  function buildChannelImageData(planes, width, height) {
    var packed = [];
    for (var c = 0; c < planes.length; c++) {
      var rows = [];
      for (var y = 0; y < height; y++) {
        rows.push(packBitsRow(planes[c].subarray(y * width, y * width + width)));
      }
      packed.push(rows);
    }
    var w = new ByteWriter();
    w.u16(1); // RLE compression
    var c2, y2;
    for (c2 = 0; c2 < packed.length; c2++) {
      for (y2 = 0; y2 < height; y2++) w.u16(packed[c2][y2].length);
    }
    for (c2 = 0; c2 < packed.length; c2++) {
      for (y2 = 0; y2 < height; y2++) w.bytes(packed[c2][y2]);
    }
    return w.concat();
  }

  function validatePlane(plane, expected, label) {
    if (!(plane instanceof Uint8Array) || plane.length !== expected) {
      throw new Error(label + ' must be a Uint8Array of length ' + expected);
    }
  }

  /* Pascal string (length-prefixed) padded so the whole thing is a
   * multiple of 4 bytes, as required for layer names. */
  function writePascalName(w, name) {
    var clean = String(name).replace(/[^\x20-\x7E]/g, '?').slice(0, 255);
    w.u8(clean.length);
    w.ascii(clean);
    var pad = (4 - ((clean.length + 1) % 4)) % 4;
    for (var i = 0; i < pad; i++) w.u8(0);
  }

  function buildLayerInfo(layers) {
    var i;
    // Pre-build each layer's channel data so record lengths are known.
    var channelSets = [];
    for (i = 0; i < layers.length; i++) {
      var l = layers[i];
      var expected = l.width * l.height;
      var planes = [];
      var ids = [];
      if (l.a) { validatePlane(l.a, expected, 'layer alpha'); planes.push(l.a); ids.push(-1); }
      validatePlane(l.r, expected, 'layer red');
      validatePlane(l.g, expected, 'layer green');
      validatePlane(l.b, expected, 'layer blue');
      planes.push(l.r); ids.push(0);
      planes.push(l.g); ids.push(1);
      planes.push(l.b); ids.push(2);
      var blocks = [];
      for (var p = 0; p < planes.length; p++) {
        blocks.push(buildChannelImageData(planes[p], l.width, l.height));
      }
      channelSets.push({ ids: ids, blocks: blocks });
    }

    var w = new ByteWriter();
    w.i32(layers.length); // layer count (positive = first layer is not alpha)
    for (i = 0; i < layers.length; i++) {
      var ly = layers[i];
      var set = channelSets[i];
      w.i32(ly.top);
      w.i32(ly.left);
      w.i32(ly.top + ly.height);
      w.i32(ly.left + ly.width);
      w.u16(set.ids.length);
      for (var ch = 0; ch < set.ids.length; ch++) {
        w.i16(set.ids[ch]);
        w.u32(set.blocks[ch].length);
      }
      w.ascii('8BIM');
      w.ascii('norm'); // normal blend mode
      w.u8(255);       // opacity: fully opaque
      w.u8(0);         // clipping: base
      w.u8(0);         // flags: visible
      w.u8(0);         // filler
      var extra = new ByteWriter();
      extra.u32(0);    // layer mask data: none
      extra.u32(0);    // blending ranges: defaults
      writePascalName(extra, ly.name || ('Layer ' + (i + 1)));
      var extraBytes = extra.concat();
      w.u32(extraBytes.length);
      w.bytes(extraBytes);
    }
    for (i = 0; i < layers.length; i++) {
      var blocks = channelSets[i].blocks;
      for (var b = 0; b < blocks.length; b++) w.bytes(blocks[b]);
    }
    var content = w.concat();
    // Layer info is padded to a multiple of 2; the enclosing layer-and-mask
    // section length to a multiple of 4.
    var padLen = content.length % 2 === 0 ? 0 : 1;
    while ((4 + content.length + padLen) % 4 !== 0) padLen += 2;
    var padded = new Uint8Array(content.length + padLen);
    padded.set(content, 0);
    return padded;
  }

  function encode(options) {
    if (!options) throw new Error('options are required');
    var width = options.width;
    var height = options.height;
    if (!Number.isInteger(width) || !Number.isInteger(height) ||
        width < 1 || height < 1 || width > MAX_DIMENSION || height > MAX_DIMENSION) {
      throw new Error('width/height must be integers between 1 and ' + MAX_DIMENSION);
    }
    var comp = options.composite;
    if (!comp) throw new Error('composite planes are required');
    var size = width * height;
    validatePlane(comp.r, size, 'composite red');
    validatePlane(comp.g, size, 'composite green');
    validatePlane(comp.b, size, 'composite blue');
    if (comp.a) validatePlane(comp.a, size, 'composite alpha');

    var layers = options.layers || [];
    for (var i = 0; i < layers.length; i++) {
      var l = layers[i];
      if (!Number.isInteger(l.width) || !Number.isInteger(l.height) ||
          l.width < 1 || l.height < 1) {
        throw new Error('each layer needs integer width/height >= 1');
      }
    }

    var w = new ByteWriter();
    // Header
    w.ascii('8BPS');
    w.u16(1);                    // version
    w.bytes([0, 0, 0, 0, 0, 0]); // reserved
    w.u16(comp.a ? 4 : 3);       // channels
    w.u32(height);
    w.u32(width);
    w.u16(8);                    // depth
    w.u16(3);                    // color mode: RGB
    // Color mode data: none
    w.u32(0);
    // Image resources: none
    w.u32(0);
    // Layer and mask information
    if (layers.length > 0) {
      var layerInfo = buildLayerInfo(layers);
      w.u32(4 + layerInfo.length);
      w.u32(layerInfo.length);
      w.bytes(layerInfo);
    } else {
      w.u32(0);
    }
    // Merged composite image data
    var planes = comp.a ? [comp.r, comp.g, comp.b, comp.a] : [comp.r, comp.g, comp.b];
    w.bytes(buildChannelImageData(planes, width, height));
    return w.concat();
  }

  global.PsdEncoder = { encode: encode };
})(typeof window !== 'undefined' ? window : globalThis);
