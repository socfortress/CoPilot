import { fileURLToPath, URL } from "node:url"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import vueJsx from "@vitejs/plugin-vue-jsx"
import svgLoader from "vite-svg-loader"
import Components from "unplugin-vue-components/vite"
const hash = Math.floor(Math.random() * 90000) + 10000
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
	build: {
		rollupOptions: {
			output: {
				entryFileNames: `[name]` + hash + `.js`,
				chunkFileNames: `[name]` + hash + `.js`,
				assetFileNames: `[name]` + hash + `.[ext]`
			}
		}
	},
	optimizeDeps: {
		include: ["fast-deep-equal"]
	}
})
