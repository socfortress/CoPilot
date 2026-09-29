import { fileURLToPath } from "node:url"
import { configDefaults, defineConfig, mergeConfig } from "vitest/config"
import viteConfig from "./vite.config"

export default defineConfig(env =>
	mergeConfig(
		viteConfig(env),
		defineConfig({
			test: {
				environment: "jsdom",
				include: ["src/**/*.spec.ts"],
				// The Cypress specs run in a browser against a real backend: `pnpm test:e2e`.
				exclude: [...configDefaults.exclude, "cypress/**"],
				root: fileURLToPath(new URL("./", import.meta.url))
			}
		})
	)
)
