/* ═ ═ ═ ═ ═ ═ ═ ═ ═ *\
|      CORE LIBS      |
\* ═ ═ ═ ═ ═ ═ ═ ═ ═ */
import { createApp } from "vue"
import { createPinia } from "pinia"
import { createPersistedState } from "pinia-plugin-persistedstate"
import ElementPlus from "element-plus"
import enEn from "element-plus/es/locale/lang/en"
// import * as ElementPlusIconsVue from "@element-plus/icons-vue"

/* ═ ═ ═ ═ ═ ═ ═ ═ ═ *\
|  THIRD PARTS LIBS   |
\* ═ ═ ═ ═ ═ ═ ═ ═ ═ */
import "balloon-css/balloon.min.css"
import "../node_modules/@mdi/font/css/materialdesignicons.min.css"
import "viewerjs/dist/viewer.css"
import VueViewer from "v-viewer"
// @ts-ignore: Unreachable code error
import vClickOutside from "v-click-outside"
import VueHighlightJS from "vue3-highlightjs"
import "highlight.js/styles/solarized-light.css"
import mavonEditor from "mavon-editor"
import VueChartkick from "vue-chartkick"
import "chartkick/chart.js"
import { createI18n } from "vue-i18n"
import i18n_messages from "./i18n.json"

/* ═ ═ ═ ═ ═ ═ ═ ═ ═ *\
|     CORE ASSETS     |
\* ═ ═ ═ ═ ═ ═ ═ ═ ═ */
import "./assets/scss/global.scss"
import "flex.box/src/flexbox.css"
import "animate.css"
import App from "@/App.vue"
import router from "./router"

const i18n = createI18n({
    locale: "us",
    messages: i18n_messages
})
const pinia = createPinia()
pinia.use(createPersistedState())
const app = createApp(App)

/* ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ *\
|  THIRD PARTS COMPONENTS |
\* ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ */
app.use(i18n)
app.use(pinia)
app.use(router)
app.use(VueChartkick)
app.use(VueViewer)
app.use(vClickOutside)
app.use(mavonEditor)
app.use(VueHighlightJS)
app.use(ElementPlus, {
    locale: enEn
})

/*
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}
*/

app.mount("#app")
