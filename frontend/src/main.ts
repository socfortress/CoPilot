import { createPinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import { createApp } from "vue"
import App from "@/App.vue"
import i18n from "@/lang"
import router from "@/router"
import "@/assets/scss/index.scss"
import "./tailwind.css"

const meta = document.createElement("meta")
meta.name = "naive-ui-style"
document.head.appendChild(meta)

const pinia = createPinia()
pinia.use(
	createPersistedState({
		key: id => `__persisted__${id}`
	})
)

const app = createApp(App)
app.use(pinia)
app.use(i18n)
app.use(router)

app.mount("#app")
