const meta = document.createElement("meta")
meta.name = "naive-ui-style"
document.head.appendChild(meta)

import { createApp } from "vue"
import { createPinia } from "pinia"
import { createI18n } from "vue-i18n"
import piniaPluginPersistedstate from "pinia-plugin-persistedstate"
import VueApexCharts from "vue3-apexcharts"
import VueGoogleMaps from "@fawmi/vue-google-maps"
// @ts-ignore
import VueVectorMap from "vuevectormap"
import "vuevectormap/src/scss/vuevectormap.scss"
import "jsvectormap/dist/maps/world-merc"

import App from "@/App.vue"
import router from "@/router"
import { type Locales, type MessageSchema, getI18NConf } from "@/lang/config"

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

const i18n = createI18n<MessageSchema, Locales>(getI18NConf())

const app = createApp(App)
app.use(pinia)
app.use(i18n)
app.use(router)
app.use(VueApexCharts)
app.use(VueGoogleMaps, {
	load: {}
})
app.use(VueVectorMap)

app.mount("#app")
