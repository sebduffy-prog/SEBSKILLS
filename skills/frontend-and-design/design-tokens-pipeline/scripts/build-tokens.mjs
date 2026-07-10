#!/usr/bin/env node
// build-tokens.mjs — multi-brand DTCG build with Style Dictionary v5.
//
// Usage:  node scripts/build-tokens.mjs [brand ...]
//         node scripts/build-tokens.mjs            # builds every brand under tokens/brands/
//         node scripts/build-tokens.mjs acme umbra # builds only the named brands
//
// Layout assumed (adjust CONFIG below to fit your repo):
//   tokens/core/**/*.tokens.json      shared, brand-agnostic scales
//   tokens/brands/<brand>/**.tokens.json   per-brand overrides (e.g. brand colours)
//   tokens/themes/<brand>.<mode>.tokens.json  optional semantic light/dark layers
//
// Output: build/<brand>/tokens.css (+ .scss, .js) — one folder per brand.
//
// Requires: npm install -D style-dictionary  (v5, ESM). Node 18+.

import StyleDictionary from 'style-dictionary';
import { readdirSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';

const TOKENS_DIR = 'tokens';
const BRANDS_DIR = join(TOKENS_DIR, 'brands');
const BUILD_DIR = 'build';

/** Return the platform config for a single brand, output into build/<brand>/. */
function platformsFor(brand) {
  const buildPath = `${BUILD_DIR}/${brand}/`;
  return {
    css: {
      transformGroup: 'css',
      buildPath,
      files: [
        {
          destination: 'tokens.css',
          format: 'css/variables',
          options: { outputReferences: true },
        },
      ],
    },
    scss: {
      transformGroup: 'scss',
      buildPath,
      files: [{ destination: '_tokens.scss', format: 'scss/variables' }],
    },
    js: {
      transformGroup: 'js',
      buildPath,
      files: [{ destination: 'tokens.js', format: 'javascript/es6' }],
    },
  };
}

/** Source globs: shared core first, then this brand, then any matching theme layers. */
function sourcesFor(brand) {
  const sources = [
    `${TOKENS_DIR}/core/**/*.tokens.json`,
    `${BRANDS_DIR}/${brand}/**/*.tokens.json`,
    `${TOKENS_DIR}/themes/${brand}.*.tokens.json`,
  ];
  return sources;
}

/** Discover brand folders when none are passed on the command line. */
function discoverBrands() {
  if (!existsSync(BRANDS_DIR)) return [];
  return readdirSync(BRANDS_DIR).filter((name) =>
    statSync(join(BRANDS_DIR, name)).isDirectory(),
  );
}

async function buildBrand(brand) {
  const sd = new StyleDictionary({
    usesDtcg: true,
    expand: { typesMap: true },
    log: { verbosity: 'default' },
    source: sourcesFor(brand),
    platforms: platformsFor(brand),
  });
  await sd.buildAllPlatforms();
  console.log(`  built ${brand} -> ${BUILD_DIR}/${brand}/`);
}

async function main() {
  const requested = process.argv.slice(2);
  const brands = requested.length ? requested : discoverBrands();

  if (brands.length === 0) {
    console.error(`No brands given and none found under ${BRANDS_DIR}/`);
    process.exit(1);
  }

  console.log(`Building tokens for: ${brands.join(', ')}`);
  for (const brand of brands) {
    await buildBrand(brand); // sequential: isolated SD instance per brand
  }
  console.log('Done.');
}

main().catch((err) => {
  console.error('Token build failed:', err);
  process.exit(1);
});
