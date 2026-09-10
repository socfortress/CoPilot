import { fileURLToPath } from "node:url"
import { configDefaults, defineConfig, mergeConfig } from "vitest/config"
import viteConfig from "./vite.config"

export default defineConfig(env =>
	mergeConfig(
		viteConfig(env),
		defineConfig({
			test: {
				environment: "jsdom",
				// Both Playwright suites: their specs import `@playwright/test`, which vitest cannot run.
				exclude: [...configDefaults.exclude, "e2e/**", "e2e-mocked/**"],
				root: fileURLToPath(new URL("./", import.meta.url))
			}
		})
	)
)
