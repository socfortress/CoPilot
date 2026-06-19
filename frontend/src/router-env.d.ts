import type { RouteMetaAuth } from "@/types/auth"
import type { Layout } from "@/types/theme"
import "vue-router"

// To ensure it is treated as a module, add at least one `export` statement
export {}

declare module "vue-router" {
	interface RouteMeta extends RouteMetaAuth {
		title?: string
		theme?: {
			layout?: Layout
			boxed?: { enabled?: boolean }
			padded?: { enabled?: boolean }
		}
		skipPin?: boolean
	}
}
