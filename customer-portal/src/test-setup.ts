import { config } from "@vue/test-utils"
import { afterEach } from "vitest"
import i18n from "@/lang"

// Every mounted component can translate (#1310), in English unless a test picks another language;
// the language is reset after each test, since vue-i18n's instance is shared.
config.global.plugins = [...(config.global.plugins ?? []), i18n]

afterEach(() => {
	i18n.global.locale.value = "en"
})
