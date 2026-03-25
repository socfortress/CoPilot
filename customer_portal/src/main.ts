import { createApp } from "vue"
import i18n from "@/lang"
import { createPinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import App from "./App.vue"
import router from "./router"

// Import basic CSS
import "./styles/main.css"

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
