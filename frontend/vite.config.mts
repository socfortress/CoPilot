import { fileURLToPath, URL } from "node:url"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import vueJsx from "@vitejs/plugin-vue-jsx"
import svgLoader from "vite-svg-loader"
import Components from "unplugin-vue-components/vite"
import fs from "fs"
// import { analyzer } from "vite-bundle-analyzer"

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [
		vue({
			script: {
				defineModel: true,
				propsDestructure: true
			}
		}),
		vueJsx(),
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
				? {
						key: fs.readFileSync("/certs/key.pem"),
						cert: fs.readFileSync("/certs/cert.pem")
				}
				: false,
		proxy: {
			"/api": {
				//target: "http://copilot-backend:5000",
                target: "http://127.0.0.1:5000", // for local development
				changeOrigin: true
			}
		}
	}
})
