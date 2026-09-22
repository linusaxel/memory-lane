// Rasterizes assets/logo-mark.svg into the app icon, splash, and favicon
// PNGs app.json points at. Re-run after any change to the mark itself.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import sharp from 'sharp';

const assetsDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'assets');
const svgTemplate = readFileSync(path.join(assetsDir, 'logo-mark.svg'), 'utf8');

const ink = { light: '#1C1917', dark: '#F2EDE4' };
const paper = { light: '#F7F4EE', dark: '#161412' };

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, alpha: 1 };
}

// Rasterize the mark alone, transparent background, at `size`px.
async function renderMark(strokeHex, size) {
  const svg = svgTemplate.replaceAll('{{STROKE}}', strokeHex);
  const density = Math.ceil((size / 100) * 72 * 2); // 2x supersample, then resize down
  return sharp(Buffer.from(svg), { density })
    .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toBuffer();
}

// Composite the mark, filling `fill` of the canvas, centered on `background`, and write it.
async function write(strokeHex, size, fill, background, file) {
  const markSize = Math.round(size * fill);
  const mark = await renderMark(strokeHex, markSize);
  const offset = Math.round((size - markSize) / 2);
  let image = sharp({
    create: { width: size, height: size, channels: 4, background: background ?? { r: 0, g: 0, b: 0, alpha: 0 } },
  }).composite([{ input: mark, left: offset, top: offset }]);
  // An opaque background means the PNG should carry no alpha channel at
  // all (iOS App Store rejects an icon with one), not just paint-through opacity.
  if (background) image = image.flatten({ background }).removeAlpha();
  await image.png().toFile(path.join(assetsDir, file));
  console.log(`wrote ${file}`);
}

async function main() {
  // App icon: opaque, light only (no icon dark variant).
  await write(ink.light, 1024, 0.82, hexToRgb(paper.light), 'icon.png');

  // Splash: mark alone, transparent, composited by expo-splash-screen onto its own backgroundColor.
  await write(ink.light, 1024, 0.82, null, 'splash-icon.png');
  await write(ink.dark, 1024, 0.82, null, 'splash-icon-dark.png');

  // Android adaptive icon: foreground (mark, safe zone) + background (flat) + monochrome (mark).
  await write(ink.light, 512, 0.6, null, 'android-icon-foreground.png');
  await write(ink.light, 512, 1, hexToRgb(paper.light), 'android-icon-background.png');
  await write(ink.light, 432, 0.6, null, 'android-icon-monochrome.png');

  // Favicon: small, opaque.
  await write(ink.light, 48, 0.82, hexToRgb(paper.light), 'favicon.png');
}

main();
