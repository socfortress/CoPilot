import { addCollection } from "@iconify/vue/offline"
import { createPinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import iconCollections from "virtual:iconify-collections"
import { createApp } from "vue"
import App from "@/App.vue"
import i18n from "@/lang"
import router from "@/router"
import "@/assets/scss/index.scss"
import "./tailwind.css"

// Icons render only from these bundled collections (see vite-plugins/iconify-collections.ts).
iconCollections.forEach(collection => addCollection(collection))

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
