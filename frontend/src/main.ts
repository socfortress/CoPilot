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
pinia.use(createPersistedState())

const app = createApp(App)
app.use(pinia)
app.use(i18n)
app.use(router)

app.mount("#app")

// Dev-only tooling. The dynamic import keeps it out of the production bundle
// entirely, and the picker relies on Vue's dev-build component metadata anyway.
if (import.meta.env.DEV) {
	import("@/dev/element-picker").then(m => m.installElementPicker())
}

// TODO-FE: search for all <style/> tags and replace them with tailwind classes
