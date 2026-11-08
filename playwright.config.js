import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'e2e',
  timeout: 120_000,
  use: { baseURL: 'http://127.0.0.1:4182/', acceptDownloads: true },
  webServer: {
    command: 'python3 -m http.server 4182 --bind 127.0.0.1 --directory dist',
    url: 'http://127.0.0.1:4182/',
    reuseExistingServer: false,
  },
});
