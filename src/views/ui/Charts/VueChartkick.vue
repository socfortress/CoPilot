<template>
    <div class="page-vuechartkick scrollable ph-20">
        <div class="page-header">
            <h1>Vue Chartkick</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Charts</el-breadcrumb-item>
                <el-breadcrumb-item>Vue Chartkick</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="card-base card-shadow--medium bg-white black-text p-30 mt-40">
            <h2 class="mt-0 mb-30">Line chart</h2>
            <line-chart :data="{ '2017-01-01': 11, '2017-01-02': 6 }"></line-chart>
        </div>
        <div class="card-base card-shadow--medium bg-white black-text p-30 mt-40">
            <h2 class="mt-0 mb-30">Pie chart</h2>
            <pie-chart
                :data="[
                    ['Blueberry', 44],
                    ['Strawberry', 23]
                ]"
            ></pie-chart>
        </div>
        <div class="card-base card-shadow--medium bg-white black-text p-30 mt-40">
            <h2 class="mt-0 mb-30">Column chart</h2>
            <column-chart
                :data="[
                    ['Sun', 32],
                    ['Mon', 46],
                    ['Tue', 28]
                ]"
            ></column-chart>
        </div>
        <div class="card-base card-shadow--medium bg-white black-text p-30 mt-40">
            <h2 class="mt-0 mb-30">Bar chart</h2>
            <bar-chart
                :data="[
                    ['Work', 32],
                    ['Play', 1492]
                ]"
            ></bar-chart>
        </div>
        <div class="card-base card-shadow--medium bg-white black-text p-30 mt-40">
            <h2 class="mt-0 mb-30">Area chart</h2>
            <area-chart :data="{ '2017-01-01': 11, '2017-01-02': 6 }"></area-chart>
        </div>
        <div class="card-base card-shadow--medium bg-white black-text p-30 mt-40">
            <h2 class="mt-0 mb-30">Scatter chart</h2>
            <scatter-chart
                :data="[
                    [174.0, 80.0],
                    [176.5, 82.3],
                    [166.5, 52.3],
                    [146.5, 32.3],
                    [126.5, 12.3],
                    [16.5, 8.3]
                ]"
                xtitle="Size"
                ytitle="Population"
            ></scatter-chart>
        </div>

        <h4>
            <a href="https://github.com/ankane/vue-chartkick" target="_blank"><i class="mdi mdi-link-variant"></i>reference</a>
        </h4>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "VueChartkickPage",
    data() {
        return {}
    }
})
</script>

<style lang="scss" scoped>
.card-base {
    height: 400px;

    & > div {
        position: relative;
    }
}
</style>
