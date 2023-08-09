import { createRouter, createWebHistory } from "vue-router"

//apps
import Dashboard from "../views/apps/Dashboard.vue"
import CryptoDashboard from "../views/apps/CryptoDashboard.vue"
import EcommerceDashboard from "../views/apps/ecommerce/Dashboard.vue"
import Calendar from "../views/apps/Calendar.vue"
import Contacts from "../views/apps/Contacts.vue"
import Gallery from "../views/apps/Gallery.vue"
import Cards from "../views/apps/Cards.vue"
import Mail from "../views/apps/Mail.vue"
import Ecommerce from "./ecommerce"
import Connectors from "../views/apps/Connectors.vue"
/*

//pages
*/
import Login from "../views/pages/authentication/Login.vue"
import Login2 from "../views/pages/authentication/Login2.vue"
import Register from "../views/pages/authentication/Register.vue"
import ForgotPassword from "../views/pages/authentication/ForgotPassword.vue"
import Profile from "../views/pages/Profile.vue"
import NotFound from "../views/pages/NotFound.vue"
import Invoice from "../views/pages/Invoice.vue"

//ui
import layout from "./layout"
import Themes from "../views/ui/Themes.vue"
import Icons from "../views/ui/Icons/Icons.vue"
import MdIcons from "../views/ui/Icons/MdIcons.vue"
import FlagIcons from "../views/ui/Icons/FlagIcons.vue"
import MultiLanguage from "../views/ui/MultiLanguage.vue"
import HelperClasses from "../views/ui/HelperClasses.vue"
import Typography from "../views/ui/Typography.vue"
import element from "./element"
import tables from "./tables"
import maps from "./maps"
import editors from "./editors"
import charts from "./charts"

import layouts from "../layout"
import { useMainStore } from "@/stores/main"
import type { StateLayout } from "@/types/layout"

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/",
            alias: "/dashboard",
            name: "dashboard",
            component: Dashboard,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["app"]
            }
        },
        {
            path: "/ecommerce-dashboard",
            name: "ecommerce-admin-dashboard",
            component: EcommerceDashboard,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "eCommerce admin dashboard",
                tags: ["app", "Ecommerce"]
            }
        },
        {
            path: "/crypto-dashboard",
            alias: "/dashboards",
            name: "crypto-dashboard",
            component: CryptoDashboard,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["app", "Crypto"]
            }
        },
        {
            path: "/connectors",
            name: "connectors",
            component: Connectors,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["app"]
            }
        },
        {
            path: "/contacts",
            name: "contacts",
            component: Contacts,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["users", "address", "book", "app"]
            }
        },
        {
            path: "/gallery",
            name: "gallery",
            component: Gallery,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["photo", "app"]
            }
        },
        {
            path: "/cards",
            name: "cards",
            component: Cards,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["app", "todo"]
            }
        },
        {
            path: "/mail",
            name: "mail",
            component: Mail,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Mail",
                tags: ["app", "email", "inbox"]
            }
        },
        Ecommerce,
        layout,
        {
            path: "/themes",
            name: "themes",
            component: Themes,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["ui"]
            }
        },
        {
            path: "/icons",
            name: "icons",
            component: Icons,
            meta: {
                auth: true,
                layout: layouts.navLeft
            },
            children: [
                {
                    path: "md-icons",
                    name: "md-icons",
                    component: MdIcons,
                    meta: {
                        auth: true,
                        layout: layouts.navLeft,
                        searchable: true,
                        title: "Material Design Icons",
                        tags: ["material design"]
                    }
                },
                {
                    path: "flag-icons",
                    name: "flag-icons",
                    component: FlagIcons,
                    meta: {
                        auth: true,
                        layout: layouts.navLeft,
                        searchable: true,
                        title: "Flag Icons",
                        tags: ["list", "ui"]
                    }
                }
            ]
        },
        {
            path: "/multi-language",
            name: "multi-language",
            component: MultiLanguage,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["ui", "translate"]
            }
        },
        {
            path: "/helper-classes",
            name: "helper-classes",
            component: HelperClasses,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Helper Classes",
                tags: ["ui"]
            }
        },
        {
            path: "/typography",
            name: "typography",
            component: Typography,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Typography",
                tags: ["ui"]
            }
        },
        element,
        tables,
        maps,
        editors,
        charts,
        {
            path: "/profile",
            name: "profile",
            component: Profile,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["pages"]
            }
        },
        {
            path: "/invoice",
            name: "invoice",
            component: Invoice,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["pages"]
            }
        },
        {
            path: "/login",
            name: "login",
            component: Login,
            meta: {
                layout: layouts.contenOnly
            }
        },
        {
            path: "/login2",
            name: "login2",
            component: Login2,
            meta: {
                layout: layouts.contenOnly
            }
        },
        {
            path: "/register",
            name: "register",
            component: Register,
            meta: {
                layout: layouts.contenOnly
            }
        },
        {
            path: "/forgot-password",
            name: "forgot-password",
            component: ForgotPassword,
            meta: {
                layout: layouts.contenOnly
            }
        },
        {
            path: "/logout",
            redirect: to => {
                auth.logout()
                return "/login"
            }
        },
        {
            path: "/:pathMatch(.*)*",
            name: "not-found",
            component: NotFound,
            meta: {
                layout: layouts.contenOnly
            }
        }
    ]
})

const l = {
    contenOnly() {
        useMainStore().setLayout(layouts.contenOnly)
    },
    navLeft() {
        useMainStore().setLayout(layouts.navLeft)
    },
    navRight() {
        useMainStore().setLayout(layouts.navRight)
    },
    navTop() {
        useMainStore().setLayout(layouts.navTop)
    },
    navBottom() {
        useMainStore().setLayout(layouts.navBottom)
    },
    set(layout: Partial<StateLayout>) {
        useMainStore().setLayout(layout)
    }
}

//insert here login logic
const auth = {
    loggedIn() {
        return useMainStore().isLogged
    },
    logout() {
        useMainStore().setLogout()
    }
}

router.beforeEach((to, from) => {
    let authrequired = false
    if (to && to.meta && to.meta.auth) authrequired = true

    //console.log('authrequired', authrequired, to.name)

    if (authrequired) {
        if (auth.loggedIn()) {
            if (to.name === "login") {
                window.location.href = "/"
                return false
            }
        } else {
            if (to.name !== "login") {
                window.location.href = "/login"
                return false
            }
        }
    } else {
        if (auth.loggedIn() && to.name === "login") {
            window.location.href = "/"
            return false
        }
    }

    if (to && to.meta && to.meta.layout) {
        l.set(to.meta.layout)
    }
})

router.afterEach((to, from) => {
    setTimeout(() => {
        useMainStore().setSplashScreen(false)
    }, 500)
})

export default router
