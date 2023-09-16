import Layout from "../views/ui/Layout/Layout.vue"
import LayoutFlexbox from "../views/ui/Layout/LayoutFlexbox.vue"
import LayoutBlank from "../views/ui/Layout/LayoutBlank.vue"
import PageHeaders from "../views/ui/Layout/PageHeaders.vue"
import LayoutSidebarRight from "../views/ui/Layout/LayoutSidebarRight.vue"
import LayoutSidebarLeft from "../views/ui/Layout/LayoutSidebarLeft.vue"
import LayoutTabbed from "../views/ui/Layout/LayoutTabbed.vue"

import layouts from "../layout"

export default {
    path: "/layout",
    name: "layout",
    component: Layout,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "flexbox",
            name: "flexbox",
            component: LayoutFlexbox,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Layout Flexbox",
                tags: ["ui", "flexbox"]
            }
        },
        {
            path: "blank",
            name: "blank",
            component: LayoutBlank,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Blank page",
                tags: ["ui", "layout"]
            }
        },
        {
            path: "page-headers",
            name: "page-headers",
            component: PageHeaders,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Page headers",
                tags: ["ui", "layout"]
            }
        },
        {
            path: "sidebar-right",
            name: "sidebar-right",
            component: LayoutSidebarRight,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Sidebar right",
                tags: ["ui", "layout"]
            }
        },
        {
            path: "sidebar-left",
            name: "sidebar-left",
            component: LayoutSidebarLeft,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Sidebar left",
                tags: ["ui", "layout"]
            }
        },
        {
            path: "tabbed",
            name: "tabbed",
            component: LayoutTabbed,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Tabbed page",
                tags: ["ui", "layout"]
            }
        }
    ]
}
