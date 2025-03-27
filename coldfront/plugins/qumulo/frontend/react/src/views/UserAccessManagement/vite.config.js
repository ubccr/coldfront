import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const dirname = import.meta.dirname;
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: `${dirname}/../../../public/`,
  base: "/static/UserAccessManagement",
  build: {
    emptyOutDir: true,
    outDir: `${dirname}/../../../dist/UserAccessManagement`,
  },
});
