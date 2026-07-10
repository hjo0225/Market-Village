// design-sync: cfg.buildCmd — produces the three generated inputs the
// converter consumes (all gitignored):
//   1. frontend/.ds-entry.ts      (named-export entry; gen-entry.mjs)
//   2. frontend/.ds-types/        (.d.ts tree via tsc — props contracts)
//   3. frontend/.ds-tailwind.css  (compiled Tailwind theme — cfg.cssEntry)
import { execFileSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = resolve(fileURLToPath(new URL('..', import.meta.url)));
const FRONTEND = join(REPO, 'frontend');
const run = (args) => execFileSync(process.execPath, args, { cwd: REPO, stdio: 'inherit' });

await import('./gen-entry.mjs');

console.error('[build-ds] tsc --emitDeclarationOnly → frontend/.ds-types/');
run([join(FRONTEND, 'node_modules', 'typescript', 'lib', 'tsc.js'), '-p', join(FRONTEND, 'tsconfig.dssync.json')]);

console.error('[build-ds] tailwind → frontend/.ds-tailwind.css');
run([
  join(FRONTEND, 'node_modules', 'tailwindcss', 'lib', 'cli.js'),
  '-c', join(REPO, '.design-sync', 'tailwind.sync.config.js'),
  '-i', join(FRONTEND, 'app', 'globals.css'),
  '-o', join(FRONTEND, '.ds-tailwind.css'),
]);
console.error('[build-ds] done');
