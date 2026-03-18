// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://rentacastle.uk',
  output: 'static',
  integrations: [sitemap()],
});
