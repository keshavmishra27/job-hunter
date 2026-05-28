import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        timeout: 120000,
        onError: (err, req, res) => {
          console.error("Proxy error:", err.message);
          res.writeHead(503);
          res.end("Backend service unavailable. Make sure uvicorn is running on port 8000");
        },
      },
    },
  },
});
