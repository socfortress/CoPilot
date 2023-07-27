<template>
    <div class="page-peity scrollable ph-20">
        <div class="page-header">
            <h1>Peity</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Charts</el-breadcrumb-item>
                <el-breadcrumb-item>Peity</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="card-base card-shadow--medium p-30 mt-40" v-if="!isIe">
            <h2 class="mt-0 mb-30">Updating</h2>
            <div class="chart-box">
                <peity :type="'line'" :options="{ width: '100%' }" :data="lineData"></peity>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-30 mt-40">
            <h2 class="mt-0 mb-30">Pie</h2>
            <div class="chart-box">
                <peity :type="'pie'" :data="'1/5'"></peity>
                <peity :type="'pie'" :data="'226/360'"></peity>
                <peity :type="'pie'" :data="'0.52/1.561'"></peity>
                <peity :type="'pie'" :data="'1,4'"></peity>
                <peity :type="'pie'" :data="'226,134'"></peity>
                <peity :type="'pie'" :data="'0.52,1.041'"></peity>
                <peity :type="'pie'" :data="'1,2,3,2,2'"></peity>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-30 mt-40">
            <h2 class="mt-0 mb-30">Donut</h2>
            <div class="chart-box">
                <peity :type="'donut'" :data="'1/5'"></peity>
                <peity :type="'donut'" :data="'226/360'"></peity>
                <peity :type="'donut'" :data="'0.52/1.561'"></peity>
                <peity :type="'donut'" :data="'1,4'"></peity>
                <peity :type="'donut'" :data="'226,134'"></peity>
                <peity :type="'donut'" :data="'0.52,1.041'"></peity>
                <peity :type="'donut'" :data="'1,2,3,2,2'"></peity>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-30 mt-40">
            <h2 class="mt-0 mb-30">Line</h2>
            <div class="chart-box">
                <peity :type="'line'" :data="'5,3,9,6,5,9,7,3,5,2'"></peity>
                <peity :type="'line'" :data="'5,3,2,-1,-3,-2,2,3,5,2'"></peity>
                <peity :type="'line'" :data="'0,-3,-6,-4,-5,-4,-7,-3,-5,-2'"></peity>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-30 mt-40">
            <h2 class="mt-0 mb-30">Bar</h2>
            <div class="chart-box">
                <peity :type="'bar'" :data="'5,3,9,6,5,9,7,3,5,2'"></peity>
                <peity :type="'bar'" :data="'5,3,2,-1,-3,-2,2,3,5,2'"></peity>
                <peity :type="'bar'" :data="'0,-3,-6,-4,-5,-4,-7,-3,-5,-2'"></peity>
            </div>
        </div>

        <div class="card-base card-shadow--medium p-30 mt-40">
            <h2 class="mt-0 mb-30">Options</h2>
            <div class="chart-box">
                <peity
                    :type="'donut'"
                    :options="{ fill: ['red', '#eeeeee'], innerRadius: 10, radius: 40 }"
                    :data="'1/7'"
                ></peity>
                <peity
                    :type="'donut'"
                    :options="{ fill: ['orange', '#eeeeee'], innerRadius: 14, radius: 36 }"
                    :data="'2/7'"
                ></peity>
                <peity
                    :type="'donut'"
                    :options="{ fill: ['yellow', '#eeeeee'], innerRadius: 16, radius: 32 }"
                    :data="'3/7'"
                ></peity>
                <peity
                    :type="'donut'"
                    :options="{ fill: ['green', '#eeeeee'], innerRadius: 18, radius: 28 }"
                    :data="'4/7'"
                ></peity>
                <peity
                    :type="'donut'"
                    :options="{ fill: ['blue', '#eeeeee'], innerRadius: 20, radius: 24 }"
                    :data="'5/7'"
                ></peity>
                <peity
                    :type="'donut'"
                    :options="{ fill: ['indigo', '#eeeeee'], innerRadius: 18, radius: 20 }"
                    :data="'6/7'"
                ></peity>
                <peity
                    :type="'donut'"
                    :options="{ fill: ['violet', '#eeeeee'], innerRadius: 15, radius: 16 }"
                    :data="'7/7'"
                ></peity>
            </div>
        </div>

        <h4>
            <a href="https://github.com/vue-bulma/peity" target="_blank"
                ><i class="mdi mdi-link-variant"></i>reference</a
            >
        </h4>
    </div>
</template>

<script>
import { detect } from "detect-browser"
const browser = detect()
import Peity from "@/components/vue-peity/Peity.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "PeityPage",
    data() {
        return {
            isIe: true,
            data: [5, 3, 9, 6, 5, 9, 7, 3, 5, 2, 5, 3, 9, 6, 5, 9, 7, 3, 5, 2]
        }
    },
    computed: {
        lineData() {
            return this.data.toString()
        }
    },
    created() {
        if (browser.name !== "ie") this.isIe = false

        setInterval(() => {
            let random = Math.round(Math.random() * 10)
            this.data.shift()
            this.data.push(random)
        }, 1000)
    },
    components: { Peity }
})
</script>

<style lang="scss">
.page-peity {
    .chart-box {
        & > * {
            margin-right: 20px;
        }
    }
}
</style>
