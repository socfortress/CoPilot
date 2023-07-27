<template>
    <div class="toolbar flex align-center justify-space-between">
        <div class="box-left box grow flex">
            <button @click="toggleSidebar" v-if="menuBurger !== 'right'" class="toggle-sidebar card-base card-shadow--small">
                <i class="mdi mdi-menu"></i>
            </button>

            <img class="logo-mini" src="@/assets/images/logo.svg" alt="logo" />

            <search class="hidden-xs-only"></search>
        </div>
        <div class="box-right flex align-center pl-10">
            <el-dropdown trigger="click" @command="onCommandLang">
                <span class="el-dropdown-link">
                    <i class="flag-icon" :class="{ ['flag-icon-' + lang]: true }"></i>
                </span>
                <template #dropdown>
                    <el-dropdown-menu>
                        <el-dropdown-item command="us"
                            ><i class="flag-icon flag-icon-us mr-15"></i>{{ $t("languages.English") }}</el-dropdown-item
                        >
                        <el-dropdown-item command="it"
                            ><i class="flag-icon flag-icon-it mr-15"></i>{{ $t("languages.Italian") }}</el-dropdown-item
                        >
                        <el-dropdown-item command="fr"
                            ><i class="flag-icon flag-icon-fr mr-15"></i>{{ $t("languages.French") }}</el-dropdown-item
                        >
                        <el-dropdown-item command="de"
                            ><i class="flag-icon flag-icon-de mr-15"></i>{{ $t("languages.German") }}</el-dropdown-item
                        >
                        <el-dropdown-item command="es"
                            ><i class="flag-icon flag-icon-es mr-15"></i>{{ $t("languages.Spanish") }}</el-dropdown-item
                        >
                        <el-dropdown-item command="cn"
                            ><i class="flag-icon flag-icon-cn mr-15"></i>{{ $t("languages.Chinese") }}</el-dropdown-item
                        >
                        <el-dropdown-item command="jp"
                            ><i class="flag-icon flag-icon-jp mr-15"></i>{{ $t("languages.Japanese") }}</el-dropdown-item
                        >
                    </el-dropdown-menu>
                </template>
            </el-dropdown>
            <button class="fullscreen-button" @click="toggleFullscreen">
                <i class="mdi mdi-fullscreen" v-if="!fullscreen"></i>
                <i class="mdi mdi-fullscreen-exit" v-if="fullscreen"></i>
            </button>
            <el-popover placement="bottom" :width="popoverWidth" trigger="click">
                <template #reference>
                    <el-badge :is-dot="true" class="notification-icon-badge">
                        <el-button class="notification-icon">
                            <i class="mdi mdi-bell"></i>
                        </el-button>
                    </el-badge>
                </template>
                <template #default>
                    <notification-box></notification-box>
                </template>
            </el-popover>
            <span class="username"><router-link to="/profile">Aurora Shenton</router-link></span>
            <el-dropdown trigger="click" @command="onCommand">
                <span class="el-dropdown-link">
                    <img src="../assets/images/avatar.jpg" class="avatar" alt="avatar" />
                </span>
                <template #dropdown>
                    <el-dropdown-menu>
                        <el-dropdown-item command="/profile"> <i class="mdi mdi-account-outline mr-10"></i> Profile </el-dropdown-item>
                        <el-dropdown-item command="/calendar"> <i class="mdi mdi-calendar mr-10"></i> Calendar </el-dropdown-item>
                        <el-dropdown-item command="/contacts">
                            <i class="mdi mdi-account-multiple-outline mr-10"></i> Contacts
                        </el-dropdown-item>
                        <el-dropdown-item command="/logout" divided> <i class="mdi mdi-logout mr-10"></i> Logout </el-dropdown-item>
                    </el-dropdown-menu>
                </template>
            </el-dropdown>

            <button
                @click="toggleSidebar"
                v-if="menuBurger === 'right'"
                class="toggle-sidebar toggle-sidebar__right card-base card-shadow--small"
            >
                <i class="mdi mdi-menu"></i>
            </button>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "@vue/runtime-core"
import NotificationBox from "../components/NotificationBox.vue"
import Search from "../components/Search.vue"
import { api as fullscreen } from "vue-fullscreen"
import type { RouteLocationRaw } from "vue-router"

export default defineComponent({
    name: "Toolbar",
    props: ["menuBurger"],
    data() {
        return {
            popoverWidth: 300,
            fullscreen: false,
            lang: "us"
        }
    },
    methods: {
        onCommandLang(lang: string) {
            if (lang.charAt(0) === "/") this.onCommand(lang)
            else this.lang = lang
        },
        onCommand(path: RouteLocationRaw) {
            this.$router.push(path)
        },
        toggleSidebar() {
            this.$emit("toggle-sidebar")
        },
        resizePopoverWidth() {
            if (window.innerWidth <= 768) {
                this.popoverWidth = 250
            } else {
                this.popoverWidth = 300
            }
        },
        toggleFullscreen() {
            fullscreen.toggle(document.querySelector("body"), {
                callback: () => {
                    this.fullscreen = fullscreen.isFullscreen
                }
            })
        }
    },
    components: {
        NotificationBox,
        Search
    },
    mounted() {
        this.fullscreen = fullscreen.isFullscreen
        this.resizePopoverWidth()
        window.addEventListener("resize", this.resizePopoverWidth)
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.resizePopoverWidth)
    }
})
</script>

<style lang="scss" scoped>
@import "../assets/scss/_variables";
@import "../assets/scss/_mixins";

.toolbar {
    width: 100%;
    height: 100%;
    padding: 0 20px;
    box-sizing: border-box;

    .username {
        margin-left: 20px;
        font-weight: bold;
        @include text-bordered-shadow();

        a {
            color: $text-color-primary;
            text-decoration: none;

            &:hover {
                color: $text-color-accent;
            }
        }
    }

    .avatar {
        border-radius: 50%;
        width: 35px;
        height: 35px;
        border: 1px solid #fff;
        margin-left: 20px;
        box-sizing: border-box;
        display: block;
        cursor: pointer;
        box-shadow:
            0 2px 5px 0 rgba(49, 49, 93, 0.1),
            0 1px 2px 0 rgba(0, 0, 0, 0.08);
        transition: box-shadow 0.5s;

        &:hover {
            box-shadow:
                0px 3px 10px 0 rgba(49, 49, 93, 0.08),
                0px 2px 7px 0 rgba(0, 0, 0, 0.08);
        }
    }

    .notification-icon {
        font-size: 20px;
        outline: none;
        padding: 0;
        background: transparent;
        border: none;
        margin-left: 20px;
        //color: #aab7c5;
        color: transparentize($text-color-primary, 0.7);
        @include text-bordered-shadow();

        &:hover {
            color: $text-color-accent;
        }
    }

    :deep() {
        .notification-icon-badge {
            sup {
                top: 4px;
            }
        }
    }

    .toggle-sidebar {
        border: 1px solid transparent;
        height: 32px;
        min-height: 32px;
        line-height: 32px;
        width: 32px;
        min-width: 32px;
        max-width: 32px;
        box-sizing: border-box;
        text-align: center;
        margin: 0;
        outline: none;
        margin-right: 5px;
        font-size: 24px;
        padding: 0;
        cursor: pointer;
        display: inline-block;
        color: $text-color-primary;
        background: white;
        display: none;
        opacity: 0;
        transition: all 0.5s;

        &__right {
            margin-right: 0px;
            margin-left: 5px;
        }

        &:hover,
        &:focus,
        &:active {
            color: $text-color-accent;
            border-color: $text-color-accent;
        }
    }

    .fullscreen-button {
        font-size: 24px;
        cursor: pointer;
        outline: none;
        padding: 0;
        background: transparent;
        border: none;
        margin-left: 20px;
        //color: #aab7c5;
        color: transparentize($text-color-primary, 0.7);
        @include text-bordered-shadow();

        &:hover {
            color: $text-color-accent;
        }
    }

    .logo-mini {
        width: 32px;
        height: 32px;
        display: none;
    }

    .el-dropdown {
        .flag-icon {
            box-shadow:
                0 2px 5px 0 rgba(49, 49, 93, 0.1),
                0 1px 2px 0 rgba(0, 0, 0, 0.08);
            cursor: pointer;
            border: 1px solid lighten($background-color, 20%);
            background-color: lighten($background-color, 20%);
        }
    }
}

@media (max-width: 650px) {
    .toolbar {
        .username {
            display: none;
        }
    }
}

@media (max-width: 768px) {
    .toolbar {
        padding: 0 10px;

        .toggle-sidebar {
            display: block;
            opacity: 1;
        }

        .fullscreen-button {
            display: none;
        }

        .logo-mini {
            display: inherit;
        }
    }
}
</style>
