import { fileURLToPath, URL } from "node:url"
import { defineConfig, loadEnv } from "vite"
import vue from "@vitejs/plugin-vue"
import vueJsx from "@vitejs/plugin-vue-jsx"
import svgLoader from "vite-svg-loader"
import Components from "unplugin-vue-components/vite"
import fs from "fs"
// import { analyzer } from "vite-bundle-analyzer"

// https://vitejs.dev/config/
export default (args: any) => {
	process.env = { ...process.env, ...loadEnv(args.mode, process.cwd()) }

	return defineConfig({
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
					: undefined,
			proxy: {
				"/api": {
					target: "http://copilot-backend:5000",
					//target: process.env.VITE_API_URL, // for local development
					changeOrigin: true
				}
			}
		}
	})
}
