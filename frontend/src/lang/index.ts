import type { LocaleCodes, MessageSchema } from "./config"
import { createI18n } from "vue-i18n"
import { getI18NConf } from "./config"

const instance = createI18n<[MessageSchema], LocaleCodes>(getI18NConf())

export default instance

export const i18nGlobal = instance.global
