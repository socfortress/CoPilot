<template>
    <div
        class="layout-container flex justify-center"
        :class="{
            column: hasColumn,
            boxed: boxed,
            'footer-above': footerAbove,
            'content-only': !navPos
        }"
    >
        <transition name="fade">
            <div class="splash-screen" v-if="splashScreen">
                <div class="wrap">
                    <img src="/socfortress_logo.svg" class="logo" alt="logo" />
                    <img src="/Ripple-2s-200px.gif" alt="loading-image" />
                </div>
            </div>
        </transition>

        <vertical-nav
            :position="navPos"
            :collapse-nav="collapseNav"
            v-model:open-sidebar="openSidebar"
            @collapse-nav-toggle="collapseNav = !collapseNav"
            @push-page="closeSidebar"
            v-if="navPos === 'left'"
        />

        <div class="container flex column box grow">
            <div class="header" v-if="toolbar === 'top'">
                <Toolbar @toggle-sidebar="openSidebar = !openSidebar" :menu-burger="navPos" />
            </div>
            <horizontal-nav :position="navPos" @push-page="closeSidebar" v-if="navPos === 'top'" />
            <div class="header" v-if="toolbar === 'bottom'">
                <Toolbar @toggle-sidebar="openSidebar = !openSidebar" :menu-burger="navPos" />
            </div>

            <div class="main box grow flex">
                <span class="main-out-border--top-left" v-if="roundedCorners"></span>
                <span class="main-out-border--top-right" v-if="roundedCorners"></span>
                <span class="main-out-border--bottom-left" v-if="roundedCorners"></span>
                <span class="main-out-border--bottom-right" v-if="roundedCorners"></span>

                <router-view v-slot="{ Component }" class="view box grow">
                    <transition :name="viewAnimation" mode="out-in">
                        <component :is="Component" />
                    </transition>
                </router-view>
            </div>

            <horizontal-nav :position="navPos" @push-page="closeSidebar" v-if="navPos === 'bottom'" style="margin-bottom: 0" />

            <FooterComp v-if="footer === 'below'" :position="footer" />
        </div>

        <vertical-nav
            :position="navPos"
            :collapse-nav="collapseNav"
            v-model:open-sidebar="openSidebar"
            @collapse-nav-toggle="collapseNav = !collapseNav"
            @push-page="closeSidebar"
            v-if="navPos === 'right'"
        />

        <FooterComp v-if="footer === 'above'" :position="footer" />

        <layout-picker :position="navPos" v-if="isLogged" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue"
import { detect } from "detect-browser"
const browser = detect()
import HorizontalNav from "./core/horizontal-nav.vue"
import VerticalNav from "./core/vertical-nav.vue"
import Toolbar from "./core/toolbar.vue"
import Footer from "./core/footer.vue"
import LayoutPicker from "./components/layout-picker.vue"
import { useMainStore } from "./stores/main"
import { EFooter, ENavPos } from "@/types/layout.d"

export default defineComponent({
    name: "App",
    data() {
        return {
            collapseNav: false,
            openSidebar: false,
            innerWidth: 0
        }
    },
    computed: {
        navPos() {
            if (this.innerWidth <= 768 && (useMainStore().navPos === ENavPos.top || useMainStore().navPos === ENavPos.bottom)) {
                return "left"
            }
            return useMainStore().navPos
        },
        toolbar() {
            return useMainStore().toolbar
        },
        footer() {
            return useMainStore().footer
        },
        boxed() {
            return useMainStore().boxed
        },
        roundedCorners() {
            return useMainStore().roundedCorners
        },
        viewAnimation() {
            return useMainStore().viewAnimation || "none"
        },
        isLogged() {
            return useMainStore().isLogged
        },
        splashScreen() {
            return useMainStore().splashScreen
        },
        footerAbove() {
            return useMainStore().footer === EFooter.above
        },
        hasColumn() {
            return useMainStore().navPos === ENavPos.top || useMainStore().navPos === ENavPos.bottom
        }
    },
    methods: {
        resizeOpenNav() {
            this.innerWidth = window.innerWidth
            if (window.innerWidth <= 768) {
                this.collapseNav = false
            }
        },
        closeSidebar() {
            this.openSidebar = false
        }
    },
    components: {
        HorizontalNav,
        VerticalNav,
        Toolbar,
        FooterComp: Footer,
        LayoutPicker
    },
    created() {
        if (browser && browser.name) document.getElementsByTagName("html")[0].classList.add(browser.name)
    },
    mounted() {
        this.resizeOpenNav()
        window.addEventListener("resize", this.resizeOpenNav)
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.resizeOpenNav)
    }
})
</script>

<style lang="scss">
@import "./assets/scss/_variables";
@import "./assets/scss/_mixins";

.layout-container {
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    overflow: hidden;
    background: $background-color;

    .container {
        overflow: hidden;

        .header {
            height: 60px;
            margin-bottom: 20px;
            margin-top: 10px;
            margin-left: 30px;
            margin-right: 30px;
        }

        .main {
            position: relative;
            overflow: hidden;
            padding: 0 30px;
        }

        .view {
            box-sizing: border-box;
            transition: all 0.4s cubic-bezier(0.55, 0, 0.1, 1);
            backface-visibility: hidden;
            /*-webkit-perspective: 1000px;*/

            & > .el-scrollbar__wrap {
                padding: 0 20px;
            }
        }
        .fade-right-enter-from {
            opacity: 0;
            transform: translate(-30px, 0);
        }
        .fade-right-leave-to {
            opacity: 0;
            transform: translate(30px, 0);
        }
        .fade-left-enter-from {
            opacity: 0;
            transform: translate(30px, 0);
        }
        .fade-left-leave-to {
            opacity: 0;
            transform: translate(-30px, 0);
        }
        .fade-top-enter-from {
            opacity: 0;
            transform: translate(0, 30px);
        }
        .fade-top-leave-to {
            opacity: 0;
            transform: translate(0, -30px);
        }
        .fade-top-in-out-enter-from,
        .fade-top-in-out-leave-to {
            opacity: 0;
            transform: translate(0, 30px);
        }
        .fade-bottom-enter-from {
            opacity: 0;
            transform: translate(0, -30px);
        }
        .fade-bottom-leave-to {
            opacity: 0;
            transform: translate(0, 30px);
        }
        .fade-bottom-in-out-enter-from,
        .fade-bottom-in-out-leave-to {
            opacity: 0;
            transform: translate(0, -30px);
        }

        .fade-enter-from,
        .fade-leave-to {
            opacity: 0;
        }

        .main-out-border {
            &--top-left,
            &--top-right {
                background: linear-gradient($background-color, rgba(230, 235, 241, 0));
                height: 16px;
                position: absolute;
                width: 8px;
                z-index: 1;
                top: 4px;
            }
            &--bottom-left,
            &--bottom-right {
                background: linear-gradient(rgba(230, 235, 241, 0), $background-color);
                height: 16px;
                position: absolute;
                width: 8px;
                z-index: 1;
                bottom: 4px;
            }

            &--top-left,
            &--bottom-left {
                left: 42px;

                &::after {
                    content: "";
                    height: 5px;
                    position: absolute;
                    right: -4px;
                    top: -4px;
                    width: 12px;
                    box-shadow: 8px 0px 0px 0px $background-color inset;
                    border-top-left-radius: 5px;
                }
            }
            &--top-right,
            &--bottom-right {
                right: 42px;

                &::after {
                    content: "";
                    height: 5px;
                    left: -4px;
                    position: absolute;
                    top: -4px;
                    width: 12px;
                    box-shadow: -8px 0px 0px 0px $background-color inset;
                    border-top-right-radius: 5px;
                }
            }

            &--bottom-left:after {
                border-radius: 0;
                border-bottom-left-radius: 5px;
            }
            &--bottom-right:after {
                border-radius: 0;
                border-bottom-right-radius: 5px;
            }

            &--bottom-left,
            &--bottom-right {
                &::after {
                    top: initial;
                    bottom: -4px;
                }
            }
        }
    }

    &.boxed {
        max-width: 1300px;
        margin: 0 auto;
        box-shadow:
            0px 0px 20px 10px rgba(0, 0, 0, 0.15),
            0px 0px 5px 0px rgba(0, 0, 0, 0.1);
    }

    &.footer-above {
        padding-bottom: 40px;
        position: relative;
    }

    &.content-only {
        .container {
            .main-out-border--top-left,
            .main-out-border--top-right,
            .main-out-border--bottom-left,
            .main-out-border--bottom-right {
                display: none;
            }
        }
    }
}

html:not(.ie) {
    .layout-container {
        .container {
            max-width: 1920px;
        }
    }
}

@media (min-width: 1920px) {
    .layout-container:not(.boxed) {
        &.column {
            .container {
                margin: 0 auto;
            }
        }
    }
}

@media (max-width: 768px) {
    .layout-container {
        .container {
            /*width: 100%;
			max-width: 100%;
			height: 100%;
			max-height: 100%;*/

            .header {
                height: 50px;
                background: #fff;
                box-shadow: 0px -20px 10px 20px rgba(0, 0, 0, 0.25);
                margin: 0;
                margin-bottom: 5px;

                .toggle-sidebar {
                    box-shadow: none !important;
                }

                .search-box {
                    & > .el-autocomplete {
                        box-shadow: none !important;
                    }
                }
            }

            .main {
                padding: 0 5px;
            }

            .view {
                max-width: 100%;

                & > .el-scrollbar__wrap {
                    padding: 0 15px;
                    padding-top: 15px;
                }
            }
            .main-out-border--top-left,
            .main-out-border--top-right,
            .main-out-border--bottom-left,
            .main-out-border--bottom-right {
                display: none;
            }
        }
    }
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.5s ease-out;
}
.fade-enter,
.fade-leave-to {
    opacity: 0;
}
</style>
