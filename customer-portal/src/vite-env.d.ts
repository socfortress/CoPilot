/// <reference types="vite/client" />

declare module "*.vue" {
	import type { DefineComponent } from "vue"

	const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, any>
	export default component
}

declare module "virtual:iconify-collections" {
	const collections: import("@iconify/types").IconifyJSON[]
	export default collections
}

declare module "*.svg" {
	import type { DefineComponent } from "vue"

	const component: DefineComponent
	export default component
}
