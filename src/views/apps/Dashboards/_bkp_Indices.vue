<template>
    <el-scrollbar class="page page-indices">
        bkp
        <div class="card-base mb-30">
            <IndicesMarquee :indices="indices" @click="setIndex" />
        </div>

        <div class="index-details-box">
            <div class="flex center demo-box bg-orange">
                <el-select v-model="currentIndex" placeholder="Select Your Index" clearable :value-key="'index'">
                    <el-option v-for="index in indices" :key="index.index" :label="index.index" :value="index"></el-option>
                </el-select>
            </div>
        </div>

        <!--BEGIN TEST-->
        <div class="box center left">
            <div class="page-header header-primary card-base card-shadow--small">
                <h1 class="title">Index Stats</h1>

                <div class="flex justify-center align-center bg-orange" v-if="currentIndex">
                    <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                        <span class="badge">
                            <i v-if="currentIndex.health === 'green'" class="mdi mdi-shield-check"></i>
                            <i v-else-if="currentIndex.health === 'yellow'" class="mdi mdi-alert"></i>
                            <i v-else-if="currentIndex.health === 'red'" class="mdi mdi-alert-decagram"></i>
                            <strong class="accent-text font-size-20">Index:</strong>
                        </span>
                        <span class="highlight font-size-20">{{ currentIndex.index }}</span>
                    </div>
                    <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                        <span class="accent-text font-size-20">Health:</span>
                        <span class="highlight font-size-20">{{ currentIndex.health }}</span>
                    </div>
                </div>
            </div>

            <div class="spacer"></div>

            <div class="card-base card-shadow--medium scrollable only-x bg-black">
                <el-row class="mt-0" :gutter="30">
                    <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
                        <div class="page-table scrollable only-y" id="affix-container">
                            <div class="page-header">
                                <h1 class="warning-text">Index Data</h1>
                            </div>

                            <div class="table-box card-base card-shadow--medium scrollable only-x">
                                <table class="styled striped">
                                    <thead>
                                        <tr>
                                            <th scope="col">Index Name</th>
                                            <th scope="col">Index Health</th>
                                            <th scope="col">Index Document Size</th>
                                            <th scope="col">Storage Size</th>
                                            <th scope="col">Replica Count</th>
                                        </tr>
                                    </thead>
                                    <tr v-for="index in filteredIndices" :key="index.id" :class="{ health: index.health }">
                                        <!-- Display the connector details in the table -->
                                        <td>{{ index.index }}</td>
                                        <td>{{ index.health }}</td>
                                        <td>{{ index.docs_count }}</td>
                                        <td>{{ index.store_size }}</td>
                                        <td>{{ index.replica_count }}</td>

                                        <!-- Add a buttton to Rotate an Index -->
                                        <td>
                                            <div class="btn-group" role="group" aria-label="Basic example">
                                                <button type="button" class="btn btn-info btn-sm">Rotate Index</button>
                                            </div>
                                        </td>
                                        <!-- Add a buttton to Delete an Index -->
                                        <td>
                                            <div class="btn-group" role="group" aria-label="Basic example">
                                                <button type="button" class="btn btn-info btn-sm" @click="deleteIndex(index.index)">
                                                    Delete Index
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </el-col>
                </el-row>

                <!-- New table to display shards -->
                <el-row class="mt-0" :gutter="30">
                    <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
                        <div class="page-table scrollable only-y" id="affix-container">
                            <div class="page-header">
                                <h1 class="warning-text">Index Shards</h1>
                            </div>

                            <div class="table-box card-base card-shadow--medium scrollable only-x">
                                <table class="styled striped">
                                    <thead>
                                        <tr>
                                            <th scope="col">Shard Index</th>
                                            <th scope="col">Shard ID</th>
                                            <th scope="col">Shard State</th>
                                            <th scope="col">Shard Size</th>
                                            <th scope="col">Shard Node</th>
                                        </tr>
                                    </thead>
                                    <tr v-for="shard in filteredShards" :key="shard.id" class="bg-accent">
                                        <!-- Display the shard details in the table -->
                                        <td>{{ shard.index }}</td>
                                        <td>{{ shard.shard }}</td>
                                        <td>{{ shard.state }}</td>
                                        <td>{{ shard.size }}</td>
                                        <td>{{ shard.node }}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </el-col>
                </el-row>
            </div>

            <div class="el-col el-col-24 el-col-xs-24 el-col-sm-12 el-col-md-12 el-col-lg-16 el-col-xl-16">
                <el-row class="chart-row">
                    <el-col :xs="24" :sm="12" :md="12" :lg="16" :xl="16" class="chart-col">
                        <div class="chart-container">
                            <div id="chart" class="chart" :style="{ height: '500px', width: '120%' }"></div>
                        </div>
                    </el-col>
                    <el-col :xs="24" :sm="12" :md="12" :lg="8" :xl="8" class="chart-col">
                        <div class="chart-container">
                            <div id="pie" class="chart pie-chart" :style="{ height: '500px', width: '200%' }"></div>
                        </div>
                    </el-col>
                </el-row>
            </div>

            <div class="el-col el-col-24 el-col-xs-24 el-col-sm-12 el-col-md-12 el-col-lg-8 el-col-xl-8 flex box grow">
                <!-- New table to display shards -->
                <el-row class="mt-0" :gutter="30">
                    <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
                        <ClusterHealth />
                    </el-col>

                    <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
                        <div class="page-table scrollable only-y" id="affix-container">
                            <div class="page-header">
                                <h1 class="warning-text">Unhealthy Indices</h1>
                            </div>

                            <div class="table-box card-base card-shadow--medium scrollable only-x">
                                <table class="styled striped hover">
                                    <thead>
                                        <tr>
                                            <th scope="col">Index Name</th>
                                            <th scope="col">Index Health</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr
                                            v-for="index in unhealthyIndices"
                                            :key="index.id"
                                            :class="{
                                                'bg-orange': index.health === 'yellow',
                                                'bg-red': index.health === 'red'
                                            }"
                                        >
                                            <!-- Display the shard details in the table -->
                                            <td>{{ index.index }}</td>

                                            <td>{{ index.health }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </el-col>
                </el-row>
            </div>
        </div>
        <!--END TEST-->
    </el-scrollbar>
</template>

<script lang="ts">
import * as echarts from "echarts"
import { Index, IndexAllocation, IndexHealth, IndexShard } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { defineComponent } from "vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"

export default defineComponent({
    data() {
        return {
            indices: [] as Index[],
            shards: [] as IndexShard[],
            indicesAllocation: [] as IndexAllocation[],
            loadingIndex: false,
            loadingShards: false,
            loadingAllocation: false,
            loadingDeleteIndex: false,
            currentIndex: null as Index | null,
            selectedValue: "",
            selectedHealth: ""
        }
    },
    computed: {
        filteredIndices() {
            return this.indices.filter((index: Index) => index.index === this.currentIndex?.index)
        },
        filteredShards() {
            return this.shards.filter((shard: IndexShard) => shard.index === this.currentIndex?.index)
        },
        unhealthyIndices() {
            return this.indices.filter((index: Index) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED)
        },
        loading() {
            return this.loadingIndex || this.loadingShards || this.loadingAllocation
        }
    },
    methods: {
        setIndex(index: Index) {
            this.currentIndex = index
        },
        initChart() {
            // Store the indicesAllocation
            const indicesAllocation = this.indicesAllocation
            // For the indicesAllocation, get the disk_used, disk_total, and timestamp for all items in the array
            let data = indicesAllocation.map(item => {
                const date = new Date(item.timestamp)
                const hours = date.getHours()
                const minutes = date.getMinutes()
                return {
                    diskUsed: item.disk_used,
                    diskTotal: item.disk_total,
                    timestamp: `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`
                }
            })

            // Sort data array by timestamp
            data.sort((a, b) => {
                const aParts = a.timestamp.split(":").map(Number)
                const bParts = b.timestamp.split(":").map(Number)
                const aDate = new Date(1970, 0, 1, aParts[0], aParts[1])
                const bDate = new Date(1970, 0, 1, bParts[0], bParts[1])
                return aDate - bDate
            })

            // Get the last 12 data points
            data = data.slice(Math.max(data.length - 12, 0))

            // Separate the data array into individual arrays for diskUsed, diskTotal, and timestamp
            const diskUsed = data.map(item => item.diskUsed)
            const diskTotal = data.map(item => item.diskTotal)
            const timestamp = data.map(item => item.timestamp)

            console.log("diskUsed: ", diskUsed)
            console.log("diskTotal: ", diskTotal)
            console.log("timestamp: ", timestamp)

            // Initialize the chart
            this.chart = echarts.init(document.getElementById("chart"))
            this.chart.setOption({
                //backgroundColor: '#394056',
                title: {
                    top: 20,
                    text: "Wazuh-Indexer Disk Usage",
                    textStyle: { fontWeight: "normal", fontSize: 16, fontFamily: "Nunito Sans" /*color: '#F1F1F3'*/ },
                    left: "1%"
                },
                tooltip: {
                    trigger: "axis",
                    axisPointer: {
                        lineStyle: {
                            /*color: '#57617B'*/
                        }
                    }
                },
                legend: {
                    top: 40,
                    icon: "rect",
                    itemWidth: 14,
                    itemHeight: 5,
                    itemGap: 13,
                    data: ["Product-A", "Product-B"],
                    right: "4%",
                    textStyle: { fontSize: 12, fontFamily: "Nunito Sans" /*color: '#F1F1F3'*/ }
                },
                grid: {
                    top: 100,
                    left: "-5px",
                    right: "30px",
                    bottom: "2%",
                    containLabel: true
                },
                xAxis: [
                    {
                        type: "category",
                        boundaryGap: false,
                        axisLine: {
                            lineStyle: {
                                /*color: '#57617B'*/
                            }
                        },
                        data: timestamp //timestamp is the x-axis
                    }
                ],
                yAxis: [
                    {
                        show: false,
                        type: "value",
                        name: "(%)",
                        axisTick: { show: false },
                        axisLine: {
                            lineStyle: {
                                /*color: '#57617B'*/
                            }
                        },
                        axisLabel: {
                            margin: 10,
                            fontSize: 14
                        },
                        splitLine: { lineStyle: { color: "#eee" /*color: '#57617B'*/ } }
                    }
                ],
                series: [
                    {
                        name: "Disk Used",
                        type: "line",
                        smooth: true,
                        symbol: "circle",
                        symbolSize: 5,
                        showSymbol: false,
                        lineStyle: { width: 1 },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(
                                0,
                                0,
                                0,
                                1,
                                [
                                    {
                                        offset: 0,
                                        color: "rgba(19, 206, 102, 0.3)"
                                    },
                                    {
                                        offset: 0.8,
                                        color: "rgba(19, 206, 102, 0)"
                                    }
                                ],
                                false
                            ),
                            shadowColor: "rgba(0, 0, 0, 0.1)",
                            shadowBlur: 10
                        },
                        itemStyle: {
                            color: "rgb(19, 206, 102)",
                            borderColor: "rgba(19, 206, 102, 0.27)",
                            borderWidth: 12
                        },
                        data: diskUsed
                    },
                    {
                        name: "Disk Total",
                        type: "line",
                        smooth: true,
                        symbol: "circle",
                        symbolSize: 5,
                        showSymbol: false,
                        lineStyle: { width: 1 },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(
                                0,
                                0,
                                0,
                                1,
                                [
                                    {
                                        offset: 0,
                                        color: "rgba(95, 143, 223, 0.3)"
                                    },
                                    {
                                        offset: 0.8,
                                        color: "rgba(95, 143, 223, 0)"
                                    }
                                ],
                                false
                            ),
                            shadowColor: "rgba(0, 0, 0, 0.1)",
                            shadowBlur: 10
                        },
                        itemStyle: {
                            color: "rgb(95, 143, 223)",
                            borderColor: "rgba(95, 143, 223, 0.2)",
                            borderWidth: 12
                        },
                        data: diskTotal
                    } /*{
        name: 'Product-C',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: { width: 1  },
        areaStyle: {

          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
              offset: 0,
              color: 'rgba(236, 32, 95, 0.3)'
            }, {
              offset: 0.8,
              color: 'rgba(236, 32, 95, 0)'
            }], false),
            shadowColor: 'rgba(0, 0, 0, 0.1)',
            shadowBlur: 10

          },
        itemStyle: {

          color: 'rgb(236, 32, 95)',
            borderColor: 'rgba(236, 32, 95, 0.2)',
            borderWidth: 12

          },
        data: [220, 182, 125, 145, 122, 191, 134, 150, 120, 110, 165, 122]
      }*/
                ]
            })
        },
        initPie() {
            // const topIndexes = this.indices.sort((a, b) => b.store_size - a.store_size).slice(0, 5)
            const topIndexes = this.indices.sort((a, b) => b.store_size - a.store_size).slice(0, 8)

            const size = topIndexes.map(index => {
                const value = parseFloat(index.store_size) / 1024 // Convert MB to GB
                return {
                    value: value,
                    name: index.index,
                    health: index.health,
                    itemStyle: {
                        color: "#3f84f6" // Custom color for each index
                    }
                }
            })
            console.log("Size", size)

            const data = topIndexes.map(index => {
                // const value = parseFloat(index.store_size) // Parse the value as a float and remvoe the decimal
                const value = parseFloat(index.store_size) / 1000000000 // Parse the value as a float and convert to GB
                return {
                    value: value,
                    name: index.index,
                    health: index.health,
                    itemStyle: {
                        color: "#3f84f6" // Custom color for each index
                    }
                }
            })
            console.log(data)

            const redIndices = data.filter(index => index.health === "red")
            const yellowIndices = data.filter(index => index.health === "yellow")
            const greenIndices = data.filter(index => index.health === "green")

            // Get the percentage of green indices
            const greenPercentage = (greenIndices.length / data.length) * 100
            const yellowPercentage = (yellowIndices.length / data.length) * 100
            const redPercentage = (redIndices.length / data.length) * 100
            console.log("Red Indices:", redIndices)
            console.log("Yellow Indices:", yellowIndices)
            console.log("Green Indices:", greenIndices)
            console.log("Green Indices Percentage:", greenPercentage)

            // const ordersValue = data.length > 0 ? data[0].value.toFixed(2) : 0 // Get the rounded value of the first item in the data array

            this.pie = echarts.init(document.getElementById("pie"))
            this.pie.setOption({
                title: {
                    top: 20,
                    text: "Index Status and Top 8 Index Sizes By GB",
                    textStyle: { fontWeight: "normal", fontSize: 16, fontFamily: "Nunito Sans" /*color: '#F1F1F3'*/ },
                    left: "1%"
                },
                tooltip: {
                    trigger: "item",
                    formatter: "{a} <br/>{b}: {c} ({d}%)"
                },
                series: [
                    {
                        name: "Index",
                        type: "pie",
                        selectedMode: "single",
                        radius: [0, "35%"],

                        label: {
                            position: "inner"
                        },
                        labelLine: {
                            show: false
                        },
                        data: [
                            {
                                // set the value as the index size
                                value: greenPercentage.toFixed(2),
                                name: "Green Indices",
                                selected: true,
                                itemStyle: { color: "rgb(19, 206, 102)" }
                            },
                            {
                                value: yellowPercentage.toFixed(2),
                                name: "Yellow Indices",
                                itemStyle: { color: "rgb(255, 255, 0)" }
                            },
                            {
                                value: redPercentage.toFixed(2),
                                name: "Red Indices",
                                itemStyle: { color: "rgb(255, 0, 0)" }
                            }
                        ]
                    },
                    {
                        name: "Index",
                        type: "pie",
                        radius: ["45%", "60%"],
                        data: size.map((item, index) => ({
                            value: item.value.toFixed(2),
                            name: item.name,
                            itemStyle: {
                                color: item.itemStyle.color
                            }
                        })),

                        itemStyle: {
                            color: "rgb(19, 206, 102)"
                        }
                    }
                ]
            })
        },
        deleteIndex(index) {
            this.loadingDeleteIndex = true

            Api.indices
                .deleteIndex(index)
                .then(res => {
                    ElMessage({
                        message: "Index was successfully deleted.",
                        type: "success"
                    })

                    this.getIndices()
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        ElMessage({
                            message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                            type: "error"
                        })
                    } else if (err.response.status === 404) {
                        ElMessage({
                            message: err.response?.data?.message || "An error occurred. Please try again later.",
                            type: "error"
                        })
                    } else {
                        ElMessage({
                            message: "An error occurred. Please try again later.",
                            type: "error"
                        })
                    }
                })
                .finally(() => {
                    this.loadingDeleteIndex = false
                })
        },
        getIndicesAllocation() {
            this.loadingAllocation = true
            Api.indices
                .getAllocation()
                .then(res => {
                    this.indicesAllocation = res.data.node_allocation
                    this.initChart()
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        ElMessage({
                            message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                            type: "error"
                        })
                    } else if (err.response.status === 404) {
                        ElMessage({
                            message: "No alerts were found.",
                            type: "error"
                        })
                    } else {
                        ElMessage({
                            message: "An error occurred. Please try again later.",
                            type: "error"
                        })
                    }
                })
                .finally(() => {
                    this.loadingAllocation = false
                })
        },
        getIndices() {
            this.loadingIndex = true
            Api.indices
                .getIndices()
                .then(res => {
                    this.indices = res.data.indices
                    this.initPie()
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        ElMessage({
                            message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                            type: "error"
                        })
                    } else if (err.response.status === 404) {
                        ElMessage({
                            message: "No alerts were found.",
                            type: "error"
                        })
                    } else {
                        ElMessage({
                            message: "An error occurred. Please try again later.",
                            type: "error"
                        })
                    }
                })
                .finally(() => {
                    this.loadingIndex = false
                })
        },
        getShards() {
            this.loadingShards = true
            Api.indices
                .getShards()
                .then(res => {
                    this.shards = res.data.shards
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        ElMessage({
                            message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                            type: "error"
                        })
                    } else if (err.response.status === 404) {
                        ElMessage({
                            message: "No alerts were found.",
                            type: "error"
                        })
                    } else {
                        ElMessage({
                            message: "An error occurred. Please try again later.",
                            type: "error"
                        })
                    }
                })
                .finally(() => {
                    this.loadingShards = false
                })
        },

        getPieChartData() {
            const topIndexes = this.indices.sort((a, b) => b.store_size - a.store_size).slice(0, 8)

            return topIndexes.map((index, i) => ({
                value: index.store_size,
                name: `p${i + 1}`,
                itemStyle: {
                    color: "#3f84f6" // Custom color for each index
                }
            }))
        }
    },
    beforeUnmount() {
        this.pie?.dispose()
        this.chart?.dispose()
    },
    created() {
        this.getIndices()
        this.getShards()
        this.getIndicesAllocation()
    },
    components: { IndicesMarquee, ClusterHealth }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";
</style>
