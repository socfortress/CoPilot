import Indices from "../views/apps/Dashboards/Indices.vue"
import layouts from "../layout"

export default {
    path: "/indices",
    name: "indices",
    component: Indices,
    meta: {
        auth: true,
        layout: layouts.navLeft,
        searchable: true,
        tags: ["simple"]
    }
}
