import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The backend only allows the origin http://localhost:5173 (app.cors.allowed-origin),
// so the dev server must keep that port.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 5173, strictPort: true },
});
