import { createApp } from "vue"
import { createPinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import App from "./App.vue"
import router from "./router"

// Import basic CSS
import "./styles/main.css"

// Setup Pinia store
const pinia = createPinia()
pinia.use(createPersistedState())

const app = createApp(App)

app.use(pinia)
app.use(router)

app.mount("#app")
