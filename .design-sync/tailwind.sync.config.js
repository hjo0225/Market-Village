// design-sync: Tailwind config for the DS bundle's compiled stylesheet.
// Reuses the app's theme verbatim; widens content so classes used only in
// authored preview cards (.design-sync/previews/) are compiled too.
// Content paths are cwd-relative — build-ds.mjs runs the CLI from the repo root.
const base = require('../frontend/tailwind.config.ts');
const cfg = base.default ?? base;
module.exports = {
  ...cfg,
  content: [
    './frontend/app/**/*.{js,ts,jsx,tsx}',
    './frontend/components/**/*.{js,ts,jsx,tsx}',
    './.design-sync/previews/**/*.{js,ts,jsx,tsx}',
  ],
};
