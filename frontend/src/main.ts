import App from "@/App.vue"
import { getI18NConf, type Locales, type MessageSchema } from "@/lang/config"
import router from "@/router"
import { createPinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import { createApp } from "vue"
import { createI18n } from "vue-i18n"

const meta = document.createElement("meta")
meta.name = "naive-ui-style"
document.head.appendChild(meta)

const pinia = createPinia()
pinia.use(
	createPersistedState({
		key: id => `__persisted__${id}`
	})
)

const i18n = createI18n<MessageSchema, Locales>(getI18NConf())

const app = createApp(App)
app.use(pinia)
app.use(i18n)
app.use(router)

app.mount("#app")
