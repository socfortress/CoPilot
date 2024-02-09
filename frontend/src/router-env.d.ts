import "vue-router"
import { Layout } from "@/types/theme.d"
import { RouteMetaAuth } from "@/types/auth.d"

// To ensure it is treated as a module, add at least one `export` statement
export {}

declare module "vue-router" {
	interface RouteMeta extends RouteMetaAuth {
		title?: string
		forceLayout?: Layout
	}
}
