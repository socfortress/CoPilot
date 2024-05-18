/// <reference types="vite/client" />

declare module "*.vue" {
	import type { DefineComponent } from "vue"
	const component: DefineComponent<{}, {}, any>
	export default component
}

declare module "*.svg" {
	import type { DefineComponent } from "vue"
	const component: DefineComponent
	export default component
}

declare module "markdown-it-highlightjs/core" {
	export { default } from "markdown-it-highlightjs/types/core.d.ts"
}

declare module "highlight.js/lib/core" {
	export { default } from "highlight.js/types/index.d.ts"
}
