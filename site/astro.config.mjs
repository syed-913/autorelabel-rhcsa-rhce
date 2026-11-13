import { readFileSync } from 'node:fs';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// The pages a release changes get the release's date as <lastmod>, so search engines come back
// to them: the home page (it shows what is new), the changelog and the install page. Other pages
// carry no date, since a wrong one is worse than none.
const latest = readFileSync(new URL('../CHANGELOG.md', import.meta.url), 'utf8').match(/^## \S+ \((\d{4}-\d{2}-\d{2})\)/m)?.[1];
const released = new Set(['/', '/changelog/', '/start/']);

export default defineConfig({
  site: 'https://autorelabel.dpdns.org',
  trailingSlash: 'always',
  output: 'static',
  integrations: [sitemap({
    serialize(item) {
      const path = new URL(item.url).pathname;
      return latest && released.has(path) ? {...item, lastmod: `${latest}T00:00:00.000Z`} : item;
    },
  })],
  build: { inlineStylesheets: 'always' },
  image: { service: { entrypoint: 'astro/assets/services/sharp' } },
  devToolbar: { enabled: false },
});
