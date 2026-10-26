import type { LocaleCodes, MessageSchema } from "./config"
import { createI18n } from "vue-i18n"
import { getI18NConf } from "./config"

// Composition mode (`legacy: false` in the options): `global.locale` is a ref.
const instance = createI18n<[MessageSchema], LocaleCodes, false>(getI18NConf())

export default instance

export const i18nGlobal = instance.global
