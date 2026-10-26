import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://syed-913.github.io',
  base: '/autorelabel-rhcsa-rhce',
  trailingSlash: 'always',
  output: 'static',
  integrations: [sitemap()],
  build: { inlineStylesheets: 'always' },
  image: { service: { entrypoint: 'astro/assets/services/sharp' } },
  devToolbar: { enabled: false },
});
