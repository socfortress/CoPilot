import Tables from "../views/ui/Tables/Tables.vue"
import Table from "../views/ui/Tables/Table.vue"
import StyledTablePage from "../views/ui/Tables/Styled.vue"
import TuiGridPage from "../views/ui/Tables/TuiGrid.vue"

import layouts from "../layout"

export default {
    path: "/tables",
    name: "tables",
    component: Tables,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "simple-table",
            name: "simple-table",
            component: Table,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                tags: ["simple"]
            }
        },
        {
            path: "styled-table",
            name: "styled-table",
            component: StyledTablePage,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Styled Table",
                tags: ["advanced"]
            }
        },
        {
            path: "tui-grid",
            name: "tui-grid",
            component: TuiGridPage,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "TUI Grid",
                tags: ["advanced"]
            }
        }
    ]
}
