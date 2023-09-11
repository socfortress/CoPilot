<template>
    <el-menu
        v-model:default-active="activeLink"
        :mode="mode"
        @select="goto"
        :collapse="isCollapse"
        :unique-opened="true"
        background-color="transparent"
        class="main-navigation-menu"
        :class="{ 'nav-collapsed': isCollapse }"
    >
        <div class="el-menu-item-group__title" style="padding-top: 4px"><span>Apps</span></div>
        <el-sub-menu index="/dashboards" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-gauge"></i><span>Dashboard</span> </template>
            <el-menu-item index="/indices">
                <span slot="title">Indicies</span>
            </el-menu-item>
            <el-menu-item index="/agents">
                <span slot="title">Agents</span>
            </el-menu-item>
            <el-menu-item index="/inputs">
                <span slot="title">Inputs</span>
            </el-menu-item>
            <el-menu-item index="/agents-bkp">
                <span slot="title">agents-bkp</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce-dashboard">
                <span slot="title">eCommerce</span>
            </el-menu-item>
            <el-menu-item index="/crypto-dashboard">
                <span slot="title">Crypto</span>
            </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/connectors"> <i class="mdi mdi-antenna"></i><span slot="title">Connectors</span> </el-menu-item>
        <el-menu-item index="/contacts"> <i class="mdi mdi-account-multiple-outline"></i><span slot="title">Contacts</span> </el-menu-item>
        <el-menu-item index="/gallery"> <i class="mdi mdi-image-multiple-outline"></i><span slot="title">Gallery</span> </el-menu-item>
        <el-menu-item index="/cards"> <i class="mdi mdi-view-dashboard-outline"></i><span slot="title">Cards</span> </el-menu-item>
        <el-menu-item index="/mail"> <i class="mdi mdi-email-outline"></i><span slot="title">Mail</span> </el-menu-item>
        <el-sub-menu index="/ecommerce" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-cart-outline"></i><span>eCommerce</span> </template>
            <el-menu-item index="/ecommerce/dashboard">
                <span slot="title">Dashboard</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/shop">
                <span slot="title">Shop</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/products">
                <span slot="title">Products</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/product-detail">
                <span slot="title">Product Detail</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/new-product">
                <span slot="title">New Product</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/account">
                <span slot="title">My Account</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/cart">
                <span slot="title">Cart</span>
            </el-menu-item>
            <el-menu-item index="/ecommerce/checkout">
                <span slot="title">Checkout</span>
            </el-menu-item>
        </el-sub-menu>

        <div class="el-menu-item-group__title"><span>User interface</span></div>
        <el-sub-menu index="layout" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-view-compact-outline"></i><span>Layout</span> </template>
            <el-menu-item index="/layout/flexbox">
                <span slot="title">Flexbox</span>
            </el-menu-item>
            <el-menu-item index="/layout/blank">
                <span slot="title">Blank page</span>
            </el-menu-item>
            <el-menu-item index="/layout/page-headers">
                <span slot="title">Page headers</span>
            </el-menu-item>
            <el-menu-item index="/layout/sidebar-right">
                <span slot="title">Sidebar right</span>
            </el-menu-item>
            <el-menu-item index="/layout/sidebar-left">
                <span slot="title">Sidebar left</span>
            </el-menu-item>
            <el-menu-item index="/layout/tabbed">
                <span slot="title">Tabbed page</span>
            </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/themes"> <i class="mdi mdi-format-color-fill"></i><span slot="title">Themes</span> </el-menu-item>
        <el-sub-menu index="1" popper-class="main-navigation-submenu" teleported>
            <template #title> <i class="mdi mdi-menu"></i><span>Multi level menu</span> </template>
            <el-menu-item index="1-1">item one (1)</el-menu-item>
            <el-menu-item index="1-2">item two (2)</el-menu-item>
            <el-menu-item index="1-3">item three (3)</el-menu-item>
            <el-sub-menu index="1-4" popper-class="main-navigation-submenu" teleported>
                <template #title>item four (4)</template>
                <el-sub-menu index="1-4-1" popper-class="main-navigation-submenu" teleported>
                    <template #title>item one (4.1)</template>
                    <el-menu-item index="1-4-1-1">item one (4.1.1)</el-menu-item>
                    <el-menu-item index="1-4-1-2">item two (4.1.2)</el-menu-item>
                    <el-menu-item index="1-4-1-3">item three (4.1.3)</el-menu-item>
                </el-sub-menu>
                <el-sub-menu index="1-4-2" popper-class="main-navigation-submenu" teleported>
                    <template #title>item two (4.2)</template>
                    <el-menu-item index="1-4-2-1">item one (4.2.1)</el-menu-item>
                    <el-menu-item index="1-4-2-2">item two (4.2.2)</el-menu-item>
                    <el-menu-item index="1-4-2-3">item three (4.2.3)</el-menu-item>
                </el-sub-menu>
                <el-menu-item index="1-4-3">item three (4-3)</el-menu-item>
                <el-menu-item index="1-4-4">item four (4-4)</el-menu-item>
                <el-menu-item index="1-4-5">item five (4-5)</el-menu-item>
                <el-menu-item index="1-4-6">item six (4-6)</el-menu-item>
                <el-menu-item index="1-4-7">item seven (4-7)</el-menu-item>
            </el-sub-menu>
        </el-sub-menu>
        <el-sub-menu index="icons" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-folder-star-outline"></i><span>Icons</span> </template>
            <el-menu-item index="/icons/md-icons">
                <span slot="title">MD Icons</span>
            </el-menu-item>
            <el-menu-item index="/icons/flag-icons">
                <span slot="title">Flag Icons</span>
            </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/multi-language"> <i class="mdi mdi-translate"></i><span slot="title">Multi language</span> </el-menu-item>
        <el-menu-item index="/typography"> <i class="mdi mdi-format-font"></i><span slot="title">Typography</span> </el-menu-item>
        <el-menu-item index="/helper-classes">
            <i class="mdi mdi-help-circle-outline"></i><span slot="title">Helper Classes</span>
        </el-menu-item>
        <el-sub-menu index="element" popper-class="main-navigation-submenu limit-height">
            <template #title> <i class="mdi mdi-shape-outline"></i><span>Element</span> </template>
            <el-menu-item index="/element/button">
                <span slot="title">Button</span>
            </el-menu-item>
            <el-menu-item index="/element/radio">
                <span slot="title">Radio</span>
            </el-menu-item>
            <el-menu-item index="/element/checkbox">
                <span slot="title">Checkbox</span>
            </el-menu-item>
            <el-menu-item index="/element/input">
                <span slot="title">Input</span>
            </el-menu-item>
            <el-menu-item index="/element/input-number">
                <span slot="title">Input Number</span>
            </el-menu-item>
            <el-menu-item index="/element/select">
                <span slot="title">Select</span>
            </el-menu-item>
            <el-menu-item index="/element/cascader">
                <span slot="title">Cascader</span>
            </el-menu-item>
            <el-menu-item index="/element/switch">
                <span slot="title">Switch</span>
            </el-menu-item>
            <el-menu-item index="/element/slider">
                <span slot="title">Slider</span>
            </el-menu-item>
            <el-menu-item index="/element/time-picker">
                <span slot="title">Time Picker</span>
            </el-menu-item>
            <el-menu-item index="/element/date-picker">
                <span slot="title">Date Picker</span>
            </el-menu-item>
            <el-menu-item index="/element/datetime-picker">
                <span slot="title">Date Time Picker</span>
            </el-menu-item>
            <el-menu-item index="/element/upload">
                <span slot="title">Upload</span>
            </el-menu-item>
            <el-menu-item index="/element/rate">
                <span slot="title">Rate</span>
            </el-menu-item>
            <el-menu-item index="/element/color-picker">
                <span slot="title">Color Picker</span>
            </el-menu-item>
            <el-menu-item index="/element/transfer">
                <span slot="title">Transfer</span>
            </el-menu-item>
            <el-menu-item index="/element/form">
                <span slot="title">Form</span>
            </el-menu-item>
            <el-menu-item index="/element/tag">
                <span slot="title">Tag</span>
            </el-menu-item>
            <el-menu-item index="/element/progress">
                <span slot="title">Progress</span>
            </el-menu-item>
            <el-menu-item index="/element/tree">
                <span slot="title">Tree</span>
            </el-menu-item>
            <el-menu-item index="/element/pagination">
                <span slot="title">Pagination</span>
            </el-menu-item>
            <el-menu-item index="/element/badge">
                <span slot="title">Badge</span>
            </el-menu-item>
            <el-menu-item index="/element/alert">
                <span slot="title">Alert</span>
            </el-menu-item>
            <el-menu-item index="/element/loading">
                <span slot="title">Loading</span>
            </el-menu-item>
            <el-menu-item index="/element/message">
                <span slot="title">Message</span>
            </el-menu-item>
            <el-menu-item index="/element/message-box">
                <span slot="title">Message Box</span>
            </el-menu-item>
            <el-menu-item index="/element/notification">
                <span slot="title">Notification</span>
            </el-menu-item>
            <el-menu-item index="/element/menu">
                <span slot="title">NavMenu</span>
            </el-menu-item>
            <el-menu-item index="/element/tabs">
                <span slot="title">Tabs</span>
            </el-menu-item>
            <el-menu-item index="/element/breadcrumb">
                <span slot="title">Breadcrumb</span>
            </el-menu-item>
            <el-menu-item index="/element/dropdown">
                <span slot="title">Dropdown</span>
            </el-menu-item>
            <el-menu-item index="/element/steps">
                <span slot="title">Steps</span>
            </el-menu-item>
            <el-menu-item index="/element/dialog">
                <span slot="title">Dialog</span>
            </el-menu-item>
            <el-menu-item index="/element/tooltip">
                <span slot="title">Tooltip</span>
            </el-menu-item>
            <el-menu-item index="/element/popover">
                <span slot="title">Popover</span>
            </el-menu-item>
            <el-menu-item index="/element/card">
                <span slot="title">Card</span>
            </el-menu-item>
            <el-menu-item index="/element/carousel">
                <span slot="title">Carousel</span>
            </el-menu-item>
            <el-menu-item index="/element/collapse">
                <span slot="title">Collapse</span>
            </el-menu-item>
            <el-menu-item index="/element/timeline">
                <span slot="title">Timeline</span>
            </el-menu-item>
        </el-sub-menu>

        <div class="el-menu-item-group__title"><span>Components</span></div>
        <el-sub-menu index="tables" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-table"></i><span>Tables</span> </template>
            <el-menu-item index="/tables/simple-table">
                <span slot="title">Basic Table</span>
            </el-menu-item>
            <el-menu-item index="/tables/styled-table">
                <span slot="title">Element UI</span>
            </el-menu-item>
            <el-menu-item index="/tables/tui-grid">
                <span slot="title">TUI Grid</span>
            </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="maps" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-map-outline"></i><span>Maps</span> </template>
            <el-menu-item index="/maps/leaflet">
                <span slot="title">Leaflet</span>
            </el-menu-item>
            <el-menu-item index="/maps/mapbox">
                <span slot="title">Mapbox</span>
            </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="editors" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-pencil-box-outline"></i><span>Editors</span> </template>
            <el-menu-item index="/editors/quill">
                <span slot="title">Quill</span>
            </el-menu-item>
            <el-menu-item index="/editors/pell">
                <span slot="title">Pell</span>
            </el-menu-item>
            <el-menu-item index="/editors/markdown">
                <span slot="title">Markdown</span>
            </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="charts" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-chart-line"></i><span>Charts</span> </template>
            <el-menu-item index="/charts/vuechartkick">
                <span slot="title">Vue Chartkick</span>
            </el-menu-item>
            <el-menu-item index="/charts/peity">
                <span slot="title">Peity</span>
            </el-menu-item>
            <el-menu-item index="/charts/echarts">
                <span slot="title">Echarts</span>
            </el-menu-item>
        </el-sub-menu>

        <div class="el-menu-item-group__title"><span>Pages</span></div>
        <el-menu-item index="/profile">
            <i class="mdi mdi-card-account-details-outline"></i><span slot="title">Profile</span>
        </el-menu-item>
        <el-sub-menu index="authentication" popper-class="main-navigation-submenu">
            <template #title> <i class="mdi mdi-lock-outline"></i><span>Authentication</span> </template>
            <el-menu-item index="/logout">
                <span slot="title">Login</span>
            </el-menu-item>
            <el-menu-item index="/login2">
                <span slot="title">Login 2</span>
            </el-menu-item>
            <el-menu-item index="/register">
                <span slot="title">Register</span>
            </el-menu-item>
            <el-menu-item index="/forgot-password">
                <span slot="title">Forgot Password</span>
            </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/invoice"> <i class="mdi mdi-file-document-edit-outline"></i><span slot="title">Invoice</span> </el-menu-item>
        <el-menu-item index="/404"> <i class="mdi mdi-alert-octagon-outline"></i><span slot="title">404</span> </el-menu-item>

        <div class="collapse-menu-btn" :class="{ collapsed: isCollapse }">
            <button @click="$emit('collapse-nav-toggle')" class="flex align-center">
                <span v-if="!isCollapse"> <i class="mdi mdi-unfold-less-vertical"></i> Collapse </span>
                <span v-if="isCollapse"> <i class="mdi mdi-unfold-more-vertical"></i></span>
            </button>
        </div>
    </el-menu>
</template>

<script lang="ts">
import { defineComponent } from "vue"
import { detect } from "detect-browser"
import { useRoute } from "vue-router"
const browser = detect()

export default defineComponent({
    name: "Nav",
    props: ["mode", "isCollapse"],
    data() {
        return {
            isIe: true,
            isEdge: true,
            activeLink: null as unknown as string
        }
    },
    methods: {
        goto(index: string) {
            if (index.charAt(0) === "/") {
                this.$router.push(index)
                this.$emit("push-page", { page: index })
            }
        },
        setLink(path: string) {
            this.activeLink = path
        }
    },
    created() {
        if (browser && browser.name !== "ie") this.isIe = false
        if (browser && browser.name !== "edge") this.isEdge = false

        const route = useRoute()
        this.setLink(route.path)
        this.$router.afterEach((to, from) => {
            this.setLink(route.path)
        })
    }
})
</script>

<style lang="scss" scoped>
@import "../assets/scss/_variables";

.el-menu {
    border: none;
}
.el-menu::before,
.el-menu::after {
    display: none;
}
.el-sub-menu,
.el-menu-item {
    .mdi {
        vertical-align: middle;
        margin-right: 5px;
        display: inline-block;
        width: 24px;
        text-align: center;
        font-size: 18px;
    }
}

.collapse-menu-btn {
    button {
        border-radius: 4px;
        border: none;
        color: $text-color-accent;
        background: lighten($text-color-accent, 30);
        font-weight: 600;
        padding: 4px 8px;
        margin-top: 20px;
        font-size: 12px;
        margin-left: 20px;
        cursor: pointer;
        white-space: nowrap;
        overflow: hidden;
        text-align: center;

        i {
            font-size: 14px;
            margin-right: 5px;
        }
    }

    &.collapsed {
        button {
            margin-left: 17px;

            i {
                margin-right: -2px;
            }
        }
    }
}
</style>

<style lang="scss">
@import "../assets/scss/_variables";

.main-navigation-menu {
    transition: width 0.5s;

    &:not(.el-menu--collapse) {
        .el-sub-menu__title,
        .el-menu-item {
            height: 40px;
            line-height: 40px;
            background-color: transparent !important;
        }

        &:not(.el-menu--horizontal) {
            .el-menu-item,
            .el-sub-menu {
                position: relative;

                &::before {
                    content: "";
                    display: block;
                    width: 0px;
                    height: 1px;
                    position: absolute;
                    bottom: 10px;
                    left: 30px;
                    background: $text-color-primary;
                    z-index: 1;
                    opacity: 0;
                    transition: all 0.7s cubic-bezier(0.55, 0, 0.1, 1);
                }
                &:hover {
                    &::before {
                        width: 100px;
                        opacity: 1;
                        //left: 50px;
                        transform: translate(20px, 0);
                    }
                }

                &.is-active {
                    &::before {
                        background: $text-color-accent;
                    }
                }
            }
        }

        .el-sub-menu.is-opened {
            //background: #edf1f6 !important;
            //background: rgba(223, 228, 234, 0.38) !important;
            position: relative;

            &::after {
                content: "";
                display: block;
                width: 2px;
                position: absolute;
                top: 40px;
                bottom: 10px;
                left: 31px;
                background: $text-color-primary;
                z-index: 1;
            }

            &::before {
                display: none;
            }

            .el-menu-item,
            .el-sub-menu {
                &::before,
                &::after {
                    display: none;
                }
            }
        }

        .el-menu-item-group__title {
            padding: 15px 0 0px 20px;
            color: transparentize($text-color-primary, 0.65);
        }
    }

    .el-sub-menu__title,
    .el-menu-item:not(.is-active) {
        color: $text-color-primary;

        i {
            color: $text-color-primary;
        }
    }

    &.el-menu--collapse {
        .el-menu-item-group__title {
            padding: 15px 0 0px 0px;
            width: 100%;
            text-align: center;
        }

        .el-sub-menu__title:hover,
        .el-menu-item:hover {
            background-color: rgba(0, 0, 0, 0.05) !important;
        }
    }

    &.el-menu--horizontal {
        white-space: nowrap;
        /*width: fit-content;
		width: max-content;*/
        overflow: hidden;
        display: table;

        & > * {
            float: inherit !important;
            display: inline-block;
        }
    }

    &.nav-collapsed {
        .el-menu-item,
        .el-sub-menu__title {
            & > span {
                display: none;
            }
        }
    }
}

.main-navigation-submenu {
    .el-menu {
        background: #fff !important;

        .el-menu-item:not(.is-active) {
            color: $text-color-primary;
        }
        .el-menu-item:hover {
            background-color: transparentize($background-color, 0.3) !important;
        }
    }
}
</style>
