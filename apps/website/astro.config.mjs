import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import cloudflare from "@astrojs/cloudflare";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://gpu-time.dlbr.workers.dev",
  output: "static",
  adapter: cloudflare(),
  devToolbar: { enabled: false },
  integrations: [react()],
  vite: { plugins: [tailwindcss()], server: { strictPort: true } },
});
