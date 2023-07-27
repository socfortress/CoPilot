import Editors from "../views/ui/Editors/Editors.vue"
import Quill from "../views/ui/Editors/Quill.vue"
import Pell from "../views/ui/Editors/Pell.vue"
import Markdown from "../views/ui/Editors/Markdown.vue"

import layouts from "../layout"

export default {
    path: "/editors",
    name: "editors",
    component: Editors,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "quill",
            name: "quill",
            component: Quill,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Quill",
                tags: ["editor"]
            }
        },
        {
            path: "pell",
            name: "pell",
            component: Pell,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Pell",
                tags: ["editor"]
            }
        },
        {
            path: "markdown",
            name: "markdown",
            component: Markdown,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Markdown",
                tags: ["editor"]
            }
        }
    ]
}
