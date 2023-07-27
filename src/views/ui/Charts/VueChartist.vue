<template>
    <el-scrollbar class="page-vuechartist">
        <div class="page-header">
            <h1>Vue Chartist</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Charts</el-breadcrumb-item>
                <el-breadcrumb-item>Vue Chartist</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <h3 class="mb-15 mt-20">Simple Line Chart</h3>
        <div class="card-base card-shadow--medium p-50 bg-white black-text" style="height: 300px">
            <vue-chartist :data="data1" :options="options1" type="Line"></vue-chartist>
        </div>

        <h3 class="mb-15 mt-50">Bi-polar Line Chart with Area Only</h3>
        <div class="card-base card-shadow--medium p-50 bg-white black-text" style="height: 300px">
            <vue-chartist :data="data2" :options="options2" type="Line"></vue-chartist>
        </div>

        <h3 class="mb-15 mt-50">Multi-line Labels</h3>
        <div class="card-base card-shadow--medium p-50 bg-white black-text" style="height: 300px">
            <vue-chartist :data="data3" :options="options3" type="Bar"></vue-chartist>
        </div>

        <h3 class="mb-15 mt-50">Donut Chart using fill rather than stroke</h3>
        <div class="card-base card-shadow--medium p-50 bg-white black-text" style="height: 300px">
            <vue-chartist :data="data4" :options="options4" type="Pie"></vue-chartist>
        </div>

        <h4>
            <a href="https://github.com/lakb248/vue-chartist" target="_blank"><i class="mdi mdi-link-variant"></i>reference</a>
        </h4>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "VueChartistPage",
    data() {
        return {
            data1: {
                labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                series: [
                    [12, 9, 7, 8, 5],
                    [2, 1, 3.5, 7, 3],
                    [1, 3, 4, 5, 6]
                ]
            },
            options1: {
                fullWidth: true,
                chartPadding: {
                    right: 40
                }
            },
            data2: {
                labels: [1, 2, 3, 4, 5, 6, 7, 8],
                series: [
                    [1, 2, 3, 1, -2, 0, 1, 0],
                    [-2, -1, -2, -1, -2.5, -1, -2, -1],
                    [0, 0, 0, 1, 2, 2.5, 2, 1],
                    [2.5, 2, 1, 0.5, 1, 0.5, -1, -2.5]
                ]
            },
            options2: {
                high: 3,
                low: -3,
                showArea: true,
                showLine: false,
                showPoint: false,
                fullWidth: true,
                axisX: {
                    showLabel: false,
                    showGrid: false
                }
            },
            data3: {
                labels: [
                    "First quarter of the year",
                    "Second quarter of the year",
                    "Third quarter of the year",
                    "Fourth quarter of the year"
                ],
                series: [
                    [60000, 40000, 80000, 70000],
                    [40000, 30000, 70000, 65000],
                    [8000, 3000, 10000, 6000]
                ]
            },
            options3: {
                seriesBarDistance: 10,
                axisX: {
                    offset: 60
                },
                axisY: {
                    offset: 80,
                    labelInterpolationFnc: function (value) {
                        return value + " CHF"
                    },
                    scaleMinSpace: 15
                }
            },
            data4: {
                series: [20, 10, 30, 40]
            },
            options4: {
                donut: true,
                donutWidth: 60,
                donutSolid: true,
                startAngle: 270,
                showLabel: true
            }
        }
    }
})
</script>

<style lang="scss">
.v-chartist-container {
    height: 100%;
}

@media (max-width: 768px) {
    .page-vuechartist {
        .p-50 {
            padding: 10px;
        }
    }
}
</style>
