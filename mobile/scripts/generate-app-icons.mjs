// Rasterizes assets/icon.svg and icon-dark.svg into the app icon, splash, and
// favicon PNGs app.json points at. Re-run after any change to the art itself.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import sharp from 'sharp';

const assetsDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'assets');
const light = readFileSync(path.join(assetsDir, 'icon.svg'), 'utf8');
const dark = readFileSync(path.join(assetsDir, 'icon-dark.svg'), 'utf8');

// The handoff's tile corner, in the art's 120-unit viewBox.
const TILE_RX = 34;

// The first <rect> is the plum tile; everything after it is the art.
const noBackground = (svg) => svg.replace(/<rect[^>]*\/>/, '');
const tileOnly = (svg) => svg.replace(/(<rect[^>]*\/>)[\s\S]*(<\/svg>)/, '$1$2');
const rounded = (svg) => svg.replace('<rect ', `<rect rx="${TILE_RX}" `);
// Android crops an adaptive icon to its middle 66%: the art shrinks into it,
// without the tile's hairline edge, which the circle would cut into lines.
const safe = (svg) =>
  noBackground(noBackground(svg))
    .replace('</defs>', '</defs><g transform="translate(20.4 20.4) scale(0.66)">')
    .replace('</svg>', '</g></svg>');
const white = (svg) => svg.replace(/fill="#[0-9a-f]+"/gi, 'fill="#ffffff"');

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

  // Splash: the whole tile, rounded. StartupLogo and LogoTile show this PNG.
  await write(rounded(light), 1024, 'splash-icon.png');
  await write(rounded(dark), 1024, 'splash-icon-dark.png');

  // Android adaptive icon: the art over the tile layer.
  await write(safe(light), 512, 'android-icon-foreground.png');
  await write(tileOnly(light), 512, 'android-icon-background.png', { opaque: true });
  await write(white(safe(light)), 432, 'android-icon-monochrome.png');

  await write(light, 48, 'favicon.png', { opaque: true });
}

main();
