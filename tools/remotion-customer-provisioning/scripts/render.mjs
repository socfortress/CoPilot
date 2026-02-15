import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import os from 'node:os';

const format = process.argv[2];
if (!format || !['mp4', 'webm'].includes(format)) {
  console.error('Usage: node scripts/render.mjs <mp4|webm>');
  process.exit(1);
}

const root = path.resolve(process.cwd());
const entry = path.join(root, 'src', 'index.ts');
const outDir = path.resolve(root, '..', '..', 'docs', 'assets', 'hero');
const outPath = path.join(outDir, `customer-provisioning-walkthrough.${format}`);
const tmpDir = path.join(os.tmpdir(), 'copilot-remotion-customer-bundle');

const serveUrl = await bundle({
  entryPoint: entry,
  outDir: tmpDir,
  webpackOverride: (config) => config,
});

const composition = await selectComposition({
  serveUrl,
  id: 'customer-provisioning-walkthrough',
  inputProps: {},
});

await renderMedia({
  composition,
  serveUrl,
  codec: format === 'webm' ? 'vp9' : 'h264',
  outputLocation: outPath,
  inputProps: {},
  crf: format === 'webm' ? 36 : 22,
  pixelFormat: 'yuv420p',
  mute: true,
});

console.log(`Rendered ${outPath}`);
