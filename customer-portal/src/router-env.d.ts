import type { I18nString } from "@/lang/config"
import type { RouteMetaAuth } from "@/types/auth"
import type { Layout } from "@/types/theme"
import "vue-router"

// To ensure it is treated as a module, add at least one `export` statement
export {}

declare module "vue-router" {
	interface RouteMeta extends RouteMetaAuth {
		/** The page's English title; other code and specs read it. */
		title?: string
		/** The title as shown (breadcrumb, pinned pages), in the user's language (#1310). */
		titleKey?: I18nString
		theme?: {
			layout?: Layout
			boxed?: { enabled?: boolean }
			padded?: { enabled?: boolean }
		}
		skipPin?: boolean
	}
}
