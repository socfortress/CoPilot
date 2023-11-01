import { fileURLToPath, URL } from "node:url"

import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import vueJsx from "@vitejs/plugin-vue-jsx"
import svgLoader from "vite-svg-loader"
import Components from "unplugin-vue-components/vite"

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
			dts: "unplugin.components.d.ts"
		})
	],
	resolve: {
		alias: {
			"@": fileURLToPath(new URL("./src", import.meta.url))
		}
	},
	optimizeDeps: {
		include: ["@fawmi/vue-google-maps", "fast-deep-equal"]
	}
})
