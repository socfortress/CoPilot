import fs from "node:fs"
import process from "node:process"
import { fileURLToPath, URL } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import vue from "@vitejs/plugin-vue"
import { defineConfig, loadEnv } from "vite"
import VueDevTools from "vite-plugin-vue-devtools"
import svgLoader from "vite-svg-loader"

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
	// Load env file based on `mode` in the current working directory.
	// Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
	process.env = { ...process.env, ...loadEnv(mode, process.cwd(), "") }

	return {
		plugins: [
			tailwindcss(),
			vue({
				script: {
					defineModel: true
				}
			}),
			VueDevTools(),
			svgLoader()
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
			port: 3001,
			https:
				fs.existsSync("/certs/key.pem") && fs.existsSync("/certs/cert.pem")
					? { key: fs.readFileSync("/certs/key.pem"), cert: fs.readFileSync("/certs/cert.pem") }
					: undefined,
			proxy: {
				"/api": {
					// target: "http://copilot-backend:5000",
					target: process.env.VITE_API_URL,
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
		},
		build: {
			rollupOptions: {
				onwarn(warning, warn) {
					if (warning.code === "PLUGIN_WARNING" && warning.message.includes('Module "node:process"')) {
						return
					}

					warn(warning)
				}
			}
		}
	}
})
