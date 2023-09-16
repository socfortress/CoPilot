import Maps from "../views/ui/Maps/Maps.vue"
import Leaflet from "../views/ui/Maps/Leaflet.vue"
import Mapbox from "../views/ui/Maps/Mapbox.vue"

import layouts from "../layout"

export default {
    path: "/maps",
    name: "maps",
    component: Maps,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "leaflet",
            name: "leaflet",
            component: Leaflet,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Leaflet",
                tags: ["maps"]
            }
        },
        {
            path: "mapbox",
            name: "mapbox",
            component: Mapbox,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Mapbox",
                tags: ["maps"]
            }
        }
        /*{
			path: 'datamaps',
			name: 'datamaps',
			component: Datamaps,
			meta: {
				auth: true,
				layout: layouts.navLeft,
				searchable: true,
				title: 'Datamaps',
				tags: ['maps']
			}
		}*/
    ]
}
