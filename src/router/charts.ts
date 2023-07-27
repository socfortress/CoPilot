import Charts from "../views/ui/Charts/Charts.vue"
import VueChartist from "../views/ui/Charts/VueChartist.vue"
import VueChartkick from "../views/ui/Charts/VueChartkick.vue"
import Peity from "../views/ui/Charts/Peity.vue"
import Echarts from "../views/ui/Charts/Echarts.vue"

import layouts from "../layout"

export default {
    path: "/charts",
    name: "charts",
    component: Charts,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "vuechartist",
            name: "vuechartist",
            component: VueChartist,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Vue Chartist",
                tags: ["ui"]
            }
        },
        {
            path: "vuechartkick",
            name: "vuechartkick",
            component: VueChartkick,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Vue Chartkick",
                tags: ["ui"]
            }
        },
        {
            path: "peity",
            name: "peity",
            component: Peity,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Peity",
                tags: ["ui"]
            }
        },
        {
            path: "echarts",
            name: "echarts",
            component: Echarts,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Echarts",
                tags: ["ui"]
            }
        }
    ]
}
