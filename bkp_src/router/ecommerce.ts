import Account from "../views/apps/ecommerce/Account.vue"
import Cart from "../views/apps/ecommerce/Cart.vue"
import Checkout from "../views/apps/ecommerce/Checkout.vue"
import Dashboard from "../views/apps/ecommerce/Dashboard.vue"
import Ecommerce from "../views/apps/ecommerce/Ecommerce.vue"
import NewProduct from "../views/apps/ecommerce/NewProduct.vue"
import ProductDetail from "../views/apps/ecommerce/ProductDetail.vue"
import Products from "../views/apps/ecommerce/Products.vue"
import Shop from "../views/apps/ecommerce/Shop.vue"

import layouts from "../layout"

export default {
    path: "/ecommerce",
    name: "ecommerce",
    component: Ecommerce,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "account",
            name: "ecommerce-account",
            component: Account,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                //layout: layouts.navTop,
                searchable: true,
                title: "eCommerce Account",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            path: "cart",
            name: "ecommerce-cart",
            component: Cart,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                //layout: layouts.navTop,
                searchable: true,
                title: "eCommerce Cart",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            path: "checkout",
            name: "ecommerce-checkout",
            component: Checkout,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                //layout: layouts.navTop,
                searchable: true,
                title: "eCommerce Checkout",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            alias: "/ecommerce",
            path: "dashboard",
            name: "ecommerce-dashboard",
            component: Dashboard,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "eCommerce Dashboard",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            path: "new-product",
            name: "ecommerce-new-product",
            component: NewProduct,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "eCommerce New Product",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            path: "product-detail",
            name: "ecommerce-product-detail",
            component: ProductDetail,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                //layout: layouts.navTop,
                searchable: true,
                title: "eCommerce Product Detail",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            path: "products",
            name: "ecommerce-products",
            component: Products,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                //layout: layouts.navTop,
                searchable: true,
                title: "eCommerce Products",
                tags: ["ecommerce", "shop", "products"]
            }
        },
        {
            path: "shop",
            name: "ecommerce-shop",
            component: Shop,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                //layout: layouts.navTop,
                searchable: true,
                title: "eCommerce Shop",
                tags: ["ecommerce", "shop", "products"]
            }
        }
    ]
}
