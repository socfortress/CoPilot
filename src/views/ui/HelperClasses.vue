<template>
    <div class="page-helper-classes scrollable ph-20">
        <div class="page-header">
            <h1>Helper Classes</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Helper Classes</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="card-base card-shadow--medium p-30 mb-40">
            <ul class="color-box">
                <li class="bg-primary white-text">.bg-primary</li>
                <li class="bg-primary-light white-text">.bg-primary-light</li>
                <li class="bg-primary-lighter">.bg-primary-lighter</li>
            </ul>
            <ul class="color-box">
                <li class="bg-accent white-text">.bg-accent</li>
                <li class="bg-accent-light">.bg-accent-light</li>
                <li class="bg-accent-lighter">.bg-accent-lighter</li>
            </ul>
            <ul class="color-box">
                <li class="bg-success white-text">.bg-success, .bg-green</li>
                <li class="bg-success-light">.bg-success-light</li>
                <li class="bg-success-lighter">.bg-success-lighter</li>
            </ul>
            <ul class="color-box">
                <li class="bg-warning white-text">.bg-warning, .bg-orange</li>
                <li class="bg-warning-light">.bg-warning-light</li>
                <li class="bg-warning-lighter">.bg-warning-lighter</li>
            </ul>
            <ul class="color-box">
                <li class="bg-danger white-text">.bg-danger, .bg-red</li>
                <li class="bg-danger-light">.bg-danger-light</li>
                <li class="bg-danger-lighter">.bg-danger-lighter</li>
            </ul>
            <ul class="color-box">
                <li class="bg-info white-text">.bg-info, .bg-grey</li>
                <li class="bg-info-light">.bg-info-light</li>
                <li class="bg-info-lighter">.bg-info-lighter</li>
            </ul>
            <ul class="color-box">
                <li class="bg-black white-text">.bg-black</li>
                <li class="bg-white">.bg-white</li>
            </ul>
        </div>

        <div class="card-base card-shadow--medium p-30">
            <div class="flex center demo-box">
                <div class="left-box">card shadow</div>
                <div class="right-box box grow c-box">
                    <div class="card-base card-shadow--small">card-shadow--small</div>
                    <div class="card-base card-shadow--medium">card-shadow--medium</div>
                    <div class="card-base card-shadow--large">card-shadow--large</div>
                    <div class="card-base card-shadow--extraLarge">card-shadow--extraLarge</div>
                </div>
            </div>
            <div class="flex center demo-box">
                <div class="left-box">align-vertical</div>
                <div class="right-box box grow align-box">
                    <div class="align-vertical scrollable p-10" style="height: 250px; min-width: 306px">
                        <div class="align-vertical-top card-base card-shadow--small p-20 m-20">align-vertical-top</div>
                        <div class="align-vertical-middle card-base card-shadow--small p-20 m-20">align-vertical-middle</div>
                        <div class="align-vertical-bottom card-base card-shadow--small p-20 m-20">align-vertical-bottom</div>
                    </div>
                </div>
            </div>

            <div class="flex center demo-box">
                <div class="left-box">box scrollable</div>
                <div class="right-box box grow">
                    <div class="scrollable" style="width: 120px; height: 80px">
                        Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore
                        magna aliquam erat volutpat. Ut wisi enim ad minim veniam.
                    </div>
                </div>
            </div>

            <div class="flex center demo-box">
                <div class="left-box">borders</div>
                <div class="right-box box grow" v-for="i in border" :key="i">
                    <div :class="i" class="b-box">{{ i }}</div>
                </div>
            </div>

            <div class="text-divider">PADDINGS ( from <strong class="mh-7">1px</strong> to <strong class="mh-7">200px</strong> )</div>
            <br />
            <div class="flex center demo-box">
                <div class="left-box">padding ex: p-20, pt-10, padding-bottom-8, padding-horizontal-5</div>
                <div class="right-box box grow" style="overflow: hidden">
                    <div class="p-box pt-10">
                        <div class="p-box-label">pt-10</div>
                    </div>
                    <div class="p-box pb-10">
                        <div class="p-box-label">pb-10</div>
                    </div>
                    <div class="p-box pr-10">
                        <div class="p-box-label">pr-10</div>
                    </div>
                    <div class="p-box pl-10">
                        <div class="p-box-label">pl-10</div>
                    </div>
                    <div class="p-box ph-10">
                        <div class="p-box-label">ph-10</div>
                    </div>
                    <div class="p-box pv-10">
                        <div class="p-box-label">pv-10</div>
                    </div>
                    <div class="p-box no-p">
                        <div class="p-box-label">no-p</div>
                    </div>
                    <div v-for="(i, index) in padding" :key="index" :class="'p-box p-' + (1 + index)">
                        <div class="p-box-label">p-{{ 1 + index }}</div>
                    </div>
                </div>
            </div>

            <div class="text-divider">MARGINS ( from <strong class="mh-7">1px</strong> to <strong class="mh-7">200px</strong> )</div>
            <br />
            <div class="flex center demo-box">
                <div class="left-box">margins ex: m-20, mt-10, margin-bottom-8, margin-horizontal-5</div>
                <div class="right-box box grow" style="overflow: hidden">
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label mt-10">mt-10</div>
                        </div>
                    </div>
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label mb-10">mb-10</div>
                        </div>
                    </div>
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label mr-10">mr-10</div>
                        </div>
                    </div>
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label ml-10">ml-10</div>
                        </div>
                    </div>
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label mh-10">mh-10</div>
                        </div>
                    </div>
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label mv-10">mv-10</div>
                        </div>
                    </div>
                    <div class="m-box-wrap">
                        <div class="m-box">
                            <div class="m-box-label no-m">no-m</div>
                        </div>
                    </div>
                    <div class="m-box-wrap" v-for="(i, index) in margin" :key="index">
                        <div class="m-box">
                            <div :class="'m-box-label m-' + (1 + index)">m-{{ 1 + index }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="text-divider">BORDER RADIUS ( from <strong class="mh-7">1px</strong> to <strong class="mh-7">50px</strong> )</div>
            <br />
            <div class="flex center demo-box">
                <div class="left-box">border-radius</div>
                <div class="right-box box grow">
                    <div class="no-b-rad br-box">no-b-rad</div>
                    <div v-for="(i, index) in borderRadius" :key="index" :class="'b-rad-' + (1 + index)" class="br-box">
                        b-rad-{{ 1 + index }}
                    </div>
                </div>
            </div>

            <div class="text-divider">OPACITY ( from <strong class="mh-7">0</strong> to <strong class="mh-7">1</strong> )</div>
            <br />
            <div class="flex center demo-box">
                <div class="left-box">opacity ex: o-0, o-1, o-055, o-70</div>
                <div class="right-box box grow">
                    <div :class="'o-0' + i + '0 o-box'" v-for="i in 9" :key="i">o-0{{ i }}0</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "HelperClasses",
    data() {
        return {
            border: ["border", "border-top", "border-right", "border-bottom", "border-left", "border-horizontal", "border-vertical"],
            padding: Array(10),
            margin: Array(10),
            borderRadius: Array(20)
        }
    }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.card-base {
    .text-divider {
        margin-top: 80px;
        margin-bottom: 5px;
    }

    .demo-box {
        margin-bottom: 40px;

        .left-box {
            width: 150px;
            padding: 20px;
            color: transparentize($text-color-primary, 0.7);
        }

        .c-box {
            background: $background-color;
            padding: 10px;

            & > div {
                margin: 20px;
                padding: 20px;
            }
        }

        .p-box {
            width: 100px;
            height: 50px;
            box-sizing: border-box;
            border: 1px solid $text-color-primary;
            background: #6ce46c;
            display: block;
            float: left;
            margin: 10px;

            .p-box-label {
                width: 100%;
                height: 100%;
                background: $background-color;
                text-align: center;
                line-height: 30px;
            }
        }

        .m-box-wrap {
            display: block;
            float: left;
            margin: 10px;
            width: 125px;
            height: 75px;

            .m-box {
                box-sizing: border-box;
                border: 1px solid $text-color-primary;
                background: #ffd383;

                .m-box-label {
                    width: 100px;
                    height: 50px;
                    background: $background-color;
                    border: 1px dashed $text-color-accent;
                    text-align: center;
                    line-height: 30px;
                }
            }
        }

        .b-box {
            background: $background-color;
            border-color: $text-color-primary;
            padding: 10px;
            margin: 10px;
            display: block;
            float: left;
        }

        .br-box {
            background: $background-color;
            border: 1px solid $text-color-primary;
            padding: 10px;
            margin: 10px;
            display: block;
            float: left;
        }

        .o-box {
            background-color: $text-color-primary;
            color: $background-color;
            padding: 10px;
            margin: 10px;
            display: block;
            float: left;
        }
    }

    .color-box {
        font-size: 16px;
        list-style: none;
        padding: 0;
        margin: 0;
        width: 210px;
        border-radius: 5px;
        overflow: hidden;
        margin-right: 15px;
        margin-bottom: 15px;
        display: inline-block;
        box-shadow:
            0 3px 6px 0 rgba(40, 40, 90, 0.09),
            0 1px 1px 0 rgba(0, 0, 0, 0.065);

        li {
            list-style: none;
            padding: 15px;
        }
    }

    .align-box {
        background: $background-color;
    }
}

@media (max-width: 768px) {
    .card-base {
        .demo-box {
            display: block;
            overflow: hidden;

            .left-box {
                padding: 20px 0;
            }

            .left-box,
            .right-box {
                width: 100%;
                display: block;
            }
        }
    }
}
</style>
