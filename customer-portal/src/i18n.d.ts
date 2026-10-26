import type { MessageSchema } from "@/lang/config"
import type { StringKeys } from "@/types/utils"

// To ensure it is treated as a module, add at least one `export` statement
export {}

declare module "@vue/runtime-core" {
	interface ComponentCustomProperties {
		$t: {
			// Firma 1: Traduzione semplice
			(key: StringKeys<MessageSchema>): string

			// Firma 2: Traduzione con numero plurale
			(key: StringKeys<MessageSchema>, plural: number): string

			// Firma 3: Traduzione con numero plurale e opzioni aggiuntive
			(key: StringKeys<MessageSchema>, plural: number, options: TranslateOptions<Locales>): string

			// Firma 4: Traduzione con messaggio predefinito
			(key: StringKeys<MessageSchema>, defaultMsg: string): string

			// Firma 5: Traduzione con messaggio predefinito e opzioni aggiuntive
			(key: StringKeys<MessageSchema>, defaultMsg: string, options: TranslateOptions<Locales>): string

			// Firma 6: Traduzione con interpolazione di lista
			(key: StringKeys<MessageSchema>, list: unknown[]): string

			// Firma 7: Traduzione con interpolazione di lista e numero plurale
			(key: StringKeys<MessageSchema>, list: unknown[], plural: number): string

			// Firma 8: Traduzione con interpolazione di lista e messaggio predefinito
			(key: StringKeys<MessageSchema>, list: unknown[], defaultMsg: string): string

			// Firma 9: Traduzione con interpolazione di lista e opzioni aggiuntive
			(key: StringKeys<MessageSchema>, list: unknown[], options: TranslateOptions<Locales>): string

			// Firma 10: Traduzione con interpolazione nominale
			(key: StringKeys<MessageSchema>, named: NamedValue): string

			// Firma 11: Traduzione con interpolazione nominale e numero plurale
			(key: StringKeys<MessageSchema>, named: NamedValue, plural: number): string

			// Firma 12: Traduzione con interpolazione nominale e messaggio predefinito
			(key: StringKeys<MessageSchema>, named: NamedValue, defaultMsg: string): string

			// Firma 13: Traduzione con interpolazione nominale e opzioni aggiuntive
			(key: StringKeys<MessageSchema>, named: NamedValue, options: TranslateOptions<Locales>): string
		}
	}
}

declare module "vue-i18n" {
	export interface DefineLocaleMessage extends MessageSchema {}
}
