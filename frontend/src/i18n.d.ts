import type { MessageSchema } from "@/lang/config"
import type { RecursiveKeyOf } from "@/types/common"

// To ensure it is treated as a module, add at least one `export` statement
export {}

declare module "@vue/runtime-core" {
	interface ComponentCustomProperties {
		$t: {
			// Firma 1: Traduzione semplice
			(key: RecursiveKeyOf<MessageSchema>): string

			// Firma 2: Traduzione con numero plurale
			(key: RecursiveKeyOf<MessageSchema>, plural: number): string

			// Firma 3: Traduzione con numero plurale e opzioni aggiuntive
			(key: RecursiveKeyOf<MessageSchema>, plural: number, options: TranslateOptions<Locales>): string

			// Firma 4: Traduzione con messaggio predefinito
			(key: RecursiveKeyOf<MessageSchema>, defaultMsg: string): string

			// Firma 5: Traduzione con messaggio predefinito e opzioni aggiuntive
			(key: RecursiveKeyOf<MessageSchema>, defaultMsg: string, options: TranslateOptions<Locales>): string

			// Firma 6: Traduzione con interpolazione di lista
			(key: RecursiveKeyOf<MessageSchema>, list: unknown[]): string

			// Firma 7: Traduzione con interpolazione di lista e numero plurale
			(key: RecursiveKeyOf<MessageSchema>, list: unknown[], plural: number): string

			// Firma 8: Traduzione con interpolazione di lista e messaggio predefinito
			(key: RecursiveKeyOf<MessageSchema>, list: unknown[], defaultMsg: string): string

			// Firma 9: Traduzione con interpolazione di lista e opzioni aggiuntive
			(key: RecursiveKeyOf<MessageSchema>, list: unknown[], options: TranslateOptions<Locales>): string

			// Firma 10: Traduzione con interpolazione nominale
			(key: RecursiveKeyOf<MessageSchema>, named: NamedValue): string

			// Firma 11: Traduzione con interpolazione nominale e numero plurale
			(key: RecursiveKeyOf<MessageSchema>, named: NamedValue, plural: number): string

			// Firma 12: Traduzione con interpolazione nominale e messaggio predefinito
			(key: RecursiveKeyOf<MessageSchema>, named: NamedValue, defaultMsg: string): string

			// Firma 13: Traduzione con interpolazione nominale e opzioni aggiuntive
			(key: RecursiveKeyOf<MessageSchema>, named: NamedValue, options: TranslateOptions<Locales>): string
		}
	}
}

declare module "vue-i18n" {
	export interface DefineLocaleMessage extends MessageSchema {}
}
