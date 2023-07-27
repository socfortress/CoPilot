import Connectors from "../views/apps/Connectors.vue"

import layouts from "../layout"

export default {
    path: "/connectors",
    name: "connectors",
    component: Connectors,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "/connectors",
            name: "connectors",
            component: Connectors,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["simple"]
            }
        }
    ]
}
