import { defineConfig, loadEnv } from 'vite';
import eslint from 'vite-plugin-eslint';
import path from 'path';

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '../../../'), '');
  const appPort = env.APP_PORT ? Number(env.APP_PORT) : 5173;
  const basePath = env.BASE_PATH
    ? `${env.BASE_PATH.replace(/^\/+|\/+$/g, '')}/`
    : '';
  const staticUrl = `/${basePath}static/`;

  return {
    server: {
      port: appPort,
      origin: 'http://localhost:' + appPort,
    },
    root: path.resolve(__dirname, 'src'),
    resolve: {
      alias: {
        '~bootstrap': path.resolve(__dirname, 'node_modules/bootstrap'),
        '~tomselect': path.resolve(__dirname, 'node_modules/tom-select'),
        '~fontawesome': path.resolve(
          __dirname,
          'node_modules/@fortawesome/fontawesome-free'
        ),
      },
    },
    plugins: [eslint()],
    base: command === 'serve' ? staticUrl : '',
    build: {
      // Where Vite will save its output files.
      // This should be added to django settings.STATICFILES_DIRS
      outDir: path.resolve(__dirname, 'bundles'),
      emptyOutDir: true,
      assetsDir: '',
      manifest: 'manifest.json',
      rollupOptions: {
        input: {
          coldfront: path.resolve(__dirname, 'src/coldfront.ts'),
        },
        output: {
          entryFileNames: `[name].js`,
          chunkFileNames: `[name].js`,
          assetFileNames: `[name].[ext]`,
        },
      },
    },
  };
});
