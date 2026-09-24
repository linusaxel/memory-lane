// Rasterizes assets/icon.svg and icon-dark.svg into the app icon, splash, and
// favicon PNGs app.json points at. Re-run after any change to the art itself.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import sharp from 'sharp';

const assetsDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'assets');
const light = readFileSync(path.join(assetsDir, 'icon.svg'), 'utf8');
const dark = readFileSync(path.join(assetsDir, 'icon-dark.svg'), 'utf8');

// StartupLogo.tsx draws the tile with the same corner radius.
const TILE_RX = 229;

const noBackground = (svg) => svg.replace(/<rect[^>]*\/>/, '');
const noSun = (svg) => svg.replace(/<circle[^>]*\/>/, '');
const rounded = (svg) => svg.replace('<rect ', `<rect rx="${TILE_RX}" `);
const white = (svg) => svg.replace(/fill="#[0-9a-f]+"/gi, 'fill="#ffffff"');
const teal = /<rect[^>]*fill="(#[0-9a-f]+)"/i.exec(light)[1];

// An opaque icon must carry no alpha channel at all (iOS App Store rejects
// one), not just paint-through opacity.
async function write(svg, size, file, { opaque = false } = {}) {
  let image = sharp(Buffer.from(svg), { density: 144 }).resize(size, size);
  if (opaque) image = image.flatten().removeAlpha();
  await image.png().toFile(path.join(assetsDir, file));
  console.log(`wrote ${file}`);
}

async function main() {
  await write(light, 1024, 'icon.png', { opaque: true });
  await write(dark, 1024, 'icon-dark.png', { opaque: true });

  // Splash: the tile without its sun. StartupLogo fades the sun in.
  await write(rounded(noSun(light)), 1024, 'splash-icon.png');
  await write(rounded(noSun(dark)), 1024, 'splash-icon-dark.png');

  // Android adaptive icon: the art over a flat teal layer.
  await write(noBackground(light), 512, 'android-icon-foreground.png');
  await write(`<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"><rect width="1024" height="1024" fill="${teal}"/></svg>`, 512, 'android-icon-background.png', { opaque: true });
  await write(white(noBackground(light)), 432, 'android-icon-monochrome.png');

  await write(light, 48, 'favicon.png', { opaque: true });
}

main();
