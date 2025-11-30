/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_API_URL: string
	// more env variables...
}

interface ImportMeta {
	readonly env: ImportMetaEnv
}

export {}

declare global {
	const __APP_ENV__: string
}
