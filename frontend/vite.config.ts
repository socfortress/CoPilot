import fs from "node:fs"
import process from "node:process"
import { fileURLToPath, URL } from "node:url"
import vue from "@vitejs/plugin-vue"
import vueJsx from "@vitejs/plugin-vue-jsx"
import Components from "unplugin-vue-components/vite"
import { defineConfig, loadEnv } from "vite"
import VueDevTools from "vite-plugin-vue-devtools"
import svgLoader from "vite-svg-loader"
// import { analyzer } from "vite-bundle-analyzer"

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
	// Load env file based on `mode` in the current working directory.
	// Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
	process.env = { ...process.env, ...loadEnv(mode, process.cwd(), "") }

	return {
		plugins: [
			vue({
				script: {
					defineModel: true
				}
			}),
			vueJsx(),
			VueDevTools(),
			svgLoader(),
			Components({
				dirs: ["src/components/cards"],
				dts: "src/unplugin.components.d.ts"
			})
			// uncomment to enable analyzer after build
			// analyzer()
		],
		resolve: {
			alias: {
				"@": fileURLToPath(new URL("./src", import.meta.url))
			}
		},
		optimizeDeps: {
			include: ["fast-deep-equal"]
		},
		server: {
			https:
				fs.existsSync("/certs/key.pem") && fs.existsSync("/certs/cert.pem")
					? { key: fs.readFileSync("/certs/key.pem"), cert: fs.readFileSync("/certs/cert.pem") }
					: undefined,
			proxy: {
				"/api": {
					// target: "http://copilot-backend:5000",
					target: process.env.VITE_API_URL, // for local development
					changeOrigin: true
				}
			}
		},
		define: {
			__APP_ENV__: JSON.stringify(process.env.APP_ENV)
		},
		css: {
			preprocessorOptions: {
				scss: {
					silenceDeprecations: ["legacy-js-api", "import"],
					api: "modern-compiler"
				}
			}
		}
	}
})
