import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://autorelabel.dpdns.org',
  trailingSlash: 'always',
  output: 'static',
  integrations: [sitemap()],
  build: { inlineStylesheets: 'always' },
  image: { service: { entrypoint: 'astro/assets/services/sharp' } },
  devToolbar: { enabled: false },
});
