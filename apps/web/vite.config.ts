import svgr from "vite-plugin-svgr";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { reactRouter } from "@react-router/dev/vite";

export default defineConfig(({ mode }) => {
  // 这里的 loadEnv 可能读不到正确路径，我们手动加上保底逻辑
  const envs = loadEnv(mode, process.cwd(), '');
  
  // 优先级：环境变量 > 默认本地后端地址
  const API_BASE_URL = envs.API_BASE_URL || "http://127.0.0.1:8000";

  console.log('🚀 前端代理目标地址:', API_BASE_URL);

  return {
    plugins: [tailwindcss(), reactRouter(), tsconfigPaths(), svgr()],
    server: {
      proxy: {
        "/api": {
          target: API_BASE_URL,
          changeOrigin: true,
          // 这里的 rewrite 非常关键：它把前端的 /api/auth/register 变成后端的 /auth/register
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
        "/storage": {
          target: 'http://127.0.0.1:9000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/storage/, ""),
        }
      }
    },
  }
});