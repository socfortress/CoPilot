<template>
    <div class="layout-picker" :class="{ open: pickerOpened, 'pos-left': position === 'right' }">
        <div class="icon-box" @click="pickerOpened = !pickerOpened">
            <i class="mdi mdi-cog"></i>
        </div>
        <div class="picker-box">
            <div class="close-btn" @click="pickerOpened = !pickerOpened">
                <i class="mdi mdi-close"></i>
            </div>

            <div class="selector-box">
                <span class="label">View animation</span>
                <el-select v-model="viewAnimation" placeholder="Select" size="small">
                    <el-option label="fade-left" value="fade-left"></el-option>
                    <el-option label="fade-right" value="fade-right"></el-option>
                    <el-option label="fade-top" value="fade-top"></el-option>
                    <el-option label="fade-top-in-out" value="fade-top-in-out"></el-option>
                    <el-option label="fade-bottom" value="fade-bottom"></el-option>
                    <el-option label="fade-bottom-in-out" value="fade-bottom-in-out"></el-option>
                    <el-option label="fade" value="fade"></el-option>
                    <el-option label="none" :value="false"></el-option>
                </el-select>
            </div>

            <div class="selector-box">
                <span class="label">Navigation</span>
                <el-select v-model="navPos" placeholder="Select" size="small">
                    <el-option label="top" value="top"></el-option>
                    <el-option label="bottom" value="bottom"></el-option>
                    <el-option label="left" value="left"></el-option>
                    <el-option label="right" value="right"></el-option>
                    <el-option label="none" :value="false"></el-option>
                </el-select>
            </div>

            <div class="selector-box">
                <span class="label">Toolbar</span>
                <el-radio-group v-model="toolbar" size="small" v-if="navPos === 'top'">
                    <el-radio-button :label="'top'">top</el-radio-button>
                    <el-radio-button :label="'bottom'">bottom</el-radio-button>
                    <el-radio-button :label="false">off</el-radio-button>
                </el-radio-group>
                <el-radio-group v-model="toolbar" size="small" v-if="navPos !== 'top'">
                    <el-radio-button :label="'bottom'">on</el-radio-button>
                    <el-radio-button :label="false">off</el-radio-button>
                </el-radio-group>
            </div>

            <div class="selector-box">
                <span class="label">Footer</span>
                <el-radio-group v-model="footer" size="small" v-if="navPos === 'left' || navPos === 'right'">
                    <el-radio-button :label="'above'">above</el-radio-button>
                    <el-radio-button :label="'below'">below</el-radio-button>
                    <el-radio-button :label="false">off</el-radio-button>
                </el-radio-group>
                <el-radio-group v-model="footer" size="small" v-if="navPos !== 'left' && navPos !== 'right'">
                    <el-radio-button :label="'below'">on</el-radio-button>
                    <el-radio-button :label="false">off</el-radio-button>
                </el-radio-group>
            </div>

            <div class="selector-box">
                <span class="label">Boxed</span>
                <el-radio-group v-model="boxed" size="small">
                    <el-radio-button :label="true">on</el-radio-button>
                    <el-radio-button :label="false">off</el-radio-button>
                </el-radio-group>
            </div>

            <div class="selector-box">
                <span class="label">Themes (vue2 version)</span>
                <a class="theme-box" href="https://pragmatic-theme-a.ddmweb.it/" target="_blank">
                    <div class="color" style="background: #ffffff"></div>
                    <div class="color" style="background: #000000"></div>
                    <div class="color" style="background: #d7195d"></div>
                </a>
                <a class="theme-box" href="https://pragmatic-theme-b.ddmweb.it/" target="_blank">
                    <div class="color" style="background: #8794a3"></div>
                    <div class="color" style="background: #ffffff"></div>
                    <div class="color" style="background: #52f17e"></div>
                </a>
                <a class="theme-box" href="https://pragmatic-theme-c.ddmweb.it/" target="_blank">
                    <div class="color" style="background: #191d24"></div>
                    <div class="color" style="background: #ffffff"></div>
                    <div class="color" style="background: #52f17e"></div>
                </a>
                <a class="theme-box" href="https://pragmatic-theme-d.ddmweb.it/" target="_blank">
                    <div class="color" style="background: #2b80f6"></div>
                    <div class="color" style="background: #ffffff"></div>
                    <div class="color" style="background: #1b2738"></div>
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import { useMainStore } from "../stores/main"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "LayoutPicker",
    props: ["position"],
    data() {
        return {
            pickerOpened: false
        }
    },
    computed: {
        navPos: {
            get() {
                return useMainStore().navPos
            },
            set(val) {
                useMainStore().setLayout({ navPos: val })
            }
        },
        toolbar: {
            get() {
                return useMainStore().toolbar
            },
            set(val) {
                useMainStore().setLayout({ toolbar: val })
            }
        },
        footer: {
            get() {
                return useMainStore().footer
            },
            set(val) {
                useMainStore().setLayout({ footer: val })
            }
        },
        boxed: {
            get() {
                return useMainStore().boxed
            },
            set(val) {
                useMainStore().setLayout({ boxed: val })
            }
        },
        roundedCorners: {
            get() {
                return useMainStore().roundedCorners
            },
            set(val) {
                useMainStore().setLayout({ roundedCorners: val })
            }
        },
        viewAnimation: {
            get() {
                return useMainStore().viewAnimation
            },
            set(val) {
                useMainStore().setLayout({ viewAnimation: val })
            }
        }
    },
    methods: {}
})
</script>

<style lang="scss">
@import "../assets/scss/_variables";
@import "../assets/scss/_mixins";

.layout-picker {
    width: 60px;
    height: 60px;
    background: lighten($background-color, 20%);
    position: fixed;
    right: -35px;
    top: 50%;
    transform: translateX(-5px) translateY(-50%);
    border-radius: 50%;
    box-shadow:
        0px 4px 20px 0px rgba(0, 0, 0, 0.08),
        0px 2px 7px 0px rgba(0, 0, 0, 0.02);
    transition: all 0.5s;
    overflow: hidden;
    z-index: 2000;

    .icon-box {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        height: 60px;
        line-height: 60px;
        text-align: center;
        font-size: 40px;
        opacity: 0.3;
        cursor: pointer;
        transform: translateX(0px) translateY(-50%);
        transition: all 0.5s;

        i::before {
            animation: spin 5s infinite linear;
        }
    }

    .picker-box {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        padding: 15px 30px;
        box-sizing: border-box;
        transform: translateX(-100%) translateY(-50%);
        transition: all 0.2s ease-in-out 0s;

        .close-btn {
            cursor: pointer;
            text-align: right;
            font-size: 20px;
            float: right;
            position: relative;
            top: -6px;
            right: -16px;
        }

        .selector-box {
            width: 100%;
            margin: 10px 0;

            & > .label {
                width: 100%;
                display: block;
            }
        }

        .theme-box {
            display: block;
            height: 30px;
            width: 40px;
            float: left;
            border-radius: 5px;
            overflow: hidden;
            margin-right: 5px;
            box-sizing: border-box;
            border: 1px solid rgba(0, 0, 0, 0.2);

            .color {
                display: block;
                width: 33.3333%;
                float: left;
                height: 100%;
            }

            &:hover {
                border: 2px solid white;
            }
        }
    }

    &.open {
        width: 255px;
        height: 405px;
        right: -35px !important;
        border-radius: 6px;
        transform: translateX(-42px) translateY(-50%);

        .icon-box {
            transform: translateX(100%) translateY(-50%);
            opacity: 0;
        }
        .picker-box {
            transform: translateX(0%) translateY(-50%);
            opacity: 1;
            transition: all 0.5s ease-in-out 0.2s;
        }
    }

    &:hover {
        right: 0;
    }

    &.pos-left {
        right: initial;
        left: 0px;
        transform: translateX(5px) translateY(-50%);

        &.open {
            transform: translateX(15px) translateY(-50%);
        }
    }
}

@keyframes spin {
    0% {
        -webkit-transform: rotate(0deg);
        transform: rotate(0deg);
    }

    100% {
        -webkit-transform: rotate(359deg);
        transform: rotate(359deg);
    }
}

@media (max-width: 768px) {
    .layout-picker {
        display: none;
    }
}
</style>
