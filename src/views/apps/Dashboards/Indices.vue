<template>
    <el-scrollbar class="page-crypto-dashboard">
        <div id="crypto-banner" class="card-base">
            <div class="marqueeInfiniteSlider">
                <ul>
                    <li v-for="index in indices" data-balloon-pos="down">
                        <i v-if="index.health === 'green'" class="mdi mdi-check-bold bg-green"></i>
                        <i v-else-if="index.health === 'yellow'" class="mdi mdi-alert-box bg-orange"></i>
                        <i v-else-if="index.health === 'red'" class="mdi mdi-alert-box bg-red"></i>
                        {{ index.index }}
                    </li>
                </ul>
            </div>
        </div>

        <!--BEGIN TEST-->
        <div class="box center left">
            <div class="page-header header-primary card-base card-shadow--small">
                <h1 class="title">Index Stats</h1>

                <div class="flex justify-center align-center bg-orange">
                    <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                        <span class="badge">
                            <i v-if="selectedHealth === 'green'" class="mdi mdi-check-bold bg-green"></i>
                            <i v-else-if="selectedHealth === 'yellow'" class="mdi mdi-alert-box bg-orange"></i>
                            <i v-else-if="selectedHealth === 'red'" class="mdi mdi-alert-box bg-red"></i>
                            <strong class="accent-text font-size-20">Index:</strong>
                        </span>
                        <span class="highlight font-size-20">{{ selectedValue }}</span>
                    </div>
                    <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                        <span class="accent-text font-size-20">Health:</span>
                        <span class="highlight font-size-20">{{ selectedHealth }}</span>
                    </div>
                </div>
            </div>

            <div class="flex center demo-box bg-orange">
                <el-select v-model="selectedValue" placeholder="Select Your Index">
                    <el-option v-for="index in indices" :key="index.index" :label="index.index" :value="index.index"></el-option>
                </el-select>
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
                                    <tr v-for="index in filteredIndices" :key="index.id" :class="getIndexRowClass(index)">
                                        <!-- Display the connector details in the table -->
                                        <td>{{ index.index }}</td>
                                        <td>{{ index.health }}</td>
                                        <td>{{ index.docs_count }}</td>
                                        <td>{{ index.store_size }}</td>
                                        <td>{{ index.replica_count }}</td>

                                        <!-- Add a buttton to Rotate an Index -->
                                        <td>
                                            <div class="btn-group" role="group" aria-label="Basic example">
                                                <button type="button" class="btn btn-info btn-sm" @click="rotateIndex(index.index)">
                                                    Rotate Index
                                                </button>
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
                        <div class="page-table scrollable only-y" id="affix-container">
                            <div class="page-header">
                                <h1 class="warning-text">Overall Health</h1>
                            </div>

                            <div class="table-box card-base card-shadow--medium scrollable only-x">
                                <table class="styled striped hover">
                                    <thead>
                                        <tr>
                                            <th scope="col">Cluster Name</th>
                                            <th scope="col">Status</th>
                                            <th scope="col">Number of Nodes</th>
                                            <th scope="col">Active Shards</th>
                                            <th scope="col">Unassigned Shards</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr
                                            v-for="health in clusterHealth"
                                            :key="health.id"
                                            :class="{
                                                'bg-green': health.status === 'green',
                                                'bg-orange': health.status === 'yellow',
                                                'bg-red': health.status === 'red'
                                            }"
                                        >
                                            <!-- Display the shard details in the table -->
                                            <td>{{ health.cluster_name }}</td>
                                            <div class="item-box item-status status-Complete">
                                                <td>{{ health.status }}</td>
                                            </div>
                                            <td>{{ health.number_of_nodes }}</td>
                                            <td>{{ health.active_shards }}</td>
                                            <td>{{ health.unassigned_shards }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
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

<script>
import axios from "axios"
import MarqueeInfinite from "marquee-infinite"
import * as echarts from "echarts"
import "cryptocoins-icons/webfont/cryptocoins.css"
import "cryptocoins-icons/webfont/cryptocoins-colors.css"
import ResizeObserver from "../../../components/vue-resize/ResizeObserver.vue"
import _throttle from "lodash/throttle"
import { defineComponent } from "@vue/runtime-core"
import Peity from "../../../components/vue-peity/Peity.vue"

export default defineComponent({
    data() {
        return {
            indices: [],
            shards: [],
            indicesAllocation: [],
            clusterHealth: [],
            loading: false,
            errorMessage: "",
            successMessage: "",
            asyncComponent: "peity",
            resized: false,
            marquee: null,
            chartWallet: null,
            chartPrice: null,
            chartCandle: null,
            selectedValue: "",
            selectedHealth: "",
            pie: null
        }
    },
    created() {
        this.getIndices()
        this.getShards()
        this.getIndicesAllocation()
        this.getClusterHealth()
    },
    computed: {
        filteredIndices() {
            return this.indices.filter(index => index.index === this.selectedValue)
        },
        filteredShards() {
            return this.shards.filter(shard => shard.index === this.selectedValue)
        },
        unhealthyIndices() {
            return this.indices.filter(index => index.health === "yellow" || index.health === "red")
        }
    },
    methods: {
        __resizeHanlder: _throttle(function (e) {
            if (this.resized) {
                this.asyncComponent = null
                this.removePeity()
                setTimeout(() => {
                    this.asyncComponent = "peity"
                }, 1000)

                if (this.chartWallet) {
                    this.chartWallet.resize()
                }
                if (this.chartPrice) {
                    this.chartPrice.resize()
                }
                if (this.chartCandle) {
                    this.chartCandle.resize()
                }
                if (this.pie) {
                    this.pie.resize()
                }
                if (this.chart) {
                    this.chart.resize()
                }
            }
            this.resized = true
        }, 700),
        removePeity() {
            const peityEl = document.querySelectorAll(".peity")
            //ie fix
            for (let i = 0; i < peityEl.length; i++) {
                peityEl[i].parentNode.removeChild(peityEl[i])
            }
        },
        initMarquee() {
            this.marquee = new MarqueeInfinite(".marqueeInfinite", {
                maxItems: 100000,
                duration: 500000000,
                direction: "horizontal",
                loop: true
            })
        },
        updateSelectedHealth() {
            const selectedIdx = this.indices.find(index => index.index === this.selectedValue)
            this.selectedHealth = selectedIdx ? selectedIdx.health : ""
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
            const path = "http://localhost:5000/graylog/indices/" + index + "/delete"
            this.loading = true
            axios
                .delete(path)
                .then(res => {
                    this.successMessage = "Index was successfully deleted."
                    this.$message({
                        message: "Index was successfully deleted.",
                        type: "success"
                    })
                    this.getIndices()
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        this.errorMessage = "Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
                    } else if (err.response.status === 404) {
                        // Extract the `message` from the response object
                        this.errorMessage = err.response.data.message
                        this.$message({
                            message: err.response.data.message,
                            type: "error"
                        })
                    } else {
                        this.errorMessage = "An error occurred. Please try again later."
                    }
                })
                .finally(() => {
                    this.loading = false
                })
        },
        getIndicesAllocation() {
            const path = "http://localhost:5000/wazuh_indexer/allocation"
            this.loading = true
            axios
                .get(path)
                .then(res => {
                    this.indicesAllocation = res.data.node_allocation
                    this.successMessage = "Indices allocation was successfully retrieved."
                    this.initChart()
                    console.log("Indices Allocation", this.indicesAllocation)
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        this.errorMessage = "Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
                    } else if (err.response.status === 404) {
                        this.errorMessage = "No alerts were found."
                    } else {
                        this.errorMessage = "An error occurred. Please try again later."
                    }
                })
                .finally(() => {
                    this.loading = false
                })
        },
        getIndices() {
            const path = "http://localhost:5000/wazuh_indexer/indices"
            this.loading = true
            axios
                .get(path)
                .then(res => {
                    this.indices = res.data.indices
                    this.successMessage = "Indices were successfully retrieved."
                    this.initPie()
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        this.errorMessage = "Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
                    } else if (err.response.status === 404) {
                        this.errorMessage = "No alerts were found."
                    } else {
                        this.errorMessage = "An error occurred. Please try again later."
                    }
                })
                .finally(() => {
                    this.loading = false
                })
        },
        getShards() {
            const path = "http://localhost:5000/wazuh_indexer/shards"
            this.loading = true
            axios
                .get(path)
                .then(res => {
                    this.shards = res.data.shards
                    this.successMessage = "Shards were successfully retrieved."
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        this.errorMessage = "Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
                    } else if (err.response.status === 404) {
                        this.errorMessage = "No alerts were found."
                    } else {
                        this.errorMessage = "An error occurred. Please try again later."
                    }
                })
                .finally(() => {
                    this.loading = false
                })
        },
        getIndexRowClass(index) {
            if (index.health === "green") {
                return "bg-green"
            } else if (index.health === "yellow") {
                return "bg-orange"
            } else if (index.health === "red") {
                return "bg-red"
            }
            return ""
        },
        getClusterHealth() {
            const path = "http://localhost:5000/wazuh_indexer/health"
            this.loading = true
            axios
                .get(path)
                .then(res => {
                    this.clusterHealth = res.data
                    this.successMessage = "Cluster health was successfully retrieved."
                    console.log("Cluster Health", this.clusterHealth)
                })
                .catch(err => {
                    if (err.response.status === 401) {
                        this.errorMessage = "Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
                    } else if (err.response.status === 404) {
                        this.errorMessage = "No alerts were found."
                    } else {
                        this.errorMessage = "An error occurred. Please try again later."
                    }
                })
                .finally(() => {
                    this.loading = false
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
    watch: {
        selectedValue() {
            this.updateSelectedHealth()
        }
    },
    async mounted() {
        setTimeout(() => {
            this.initMarquee()
        }, 100)

        setTimeout(() => {
            //this.initChartPrice()
        }, 500)

        setTimeout(() => {
            //this.initChartCandle()
        }, 500)
    },
    beforeUnmount() {
        if (this.chartWallet) {
            this.chartWallet.dispose()
            this.chartWallet = null
        }
        if (this.chartPrice) {
            this.chartPrice.dispose()
            this.chartPrice = null
        }
        if (this.chartCandle) {
            this.chartCandle.dispose()
            this.chartCandle = null
        }
        if (!this.pie) {
            return
        }
        if (!this.chart) {
            return
        }

        this.pie.dispose()
        this.chart.dispose()
    },
    components: { ResizeObserver, Peity }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.chart-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
}

.chart-col {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}

.chart-container {
    width: 100%;
}

.chart {
    width: 100%;
}

.pie-chart {
    flex-grow: 1;
}
.marqueeInfiniteSlider {
    display: flex;
    animation: marquee 20s infinite linear;
    white-space: nowrap;
}

@keyframes marquee {
    0% {
        transform: translateX(0);
    }
    100% {
        transform: translateX(-100%);
    }
}

.chart-wallet-box > div {
    margin-left: 1%;
}

.wallet-box {
    border-right: 2px solid $text-color-primary;
    height: 500px;

    .select-wallet {
        background: $text-color-primary;
        color: $background-color;
        height: 70px;
        overflow: hidden;
        position: relative;
        z-index: 1;

        .wallet-item {
            background: $text-color-primary;
            color: $background-color;
            height: 70px;

            .icon {
                width: 70px;
                line-height: 70px;
                font-size: 35px;
            }

            .coin {
                .title {
                    font-weight: bold;
                }
            }

            .arrow {
                background: transparentize($background-color, 0.9);
                color: transparentize($background-color, 0.8);
                width: 70px;
                line-height: 70px;
                font-size: 40px;
                cursor: pointer;

                &:hover {
                    background: transparentize($background-color, 0.8);
                    color: transparentize($text-color-primary, 0.1);
                }
            }
        }

        .wallet-list {
            display: none;
            background: $text-color-primary;
            position: absolute;
            top: 70px;
            left: 0;
            right: 0;

            .wallet-item {
                background: transparentize($background-color, 0.9);
            }
        }

        &.open {
            overflow: inherit;

            .wallet-list {
                display: block;
            }
        }
    }

    .content {
        .portfolio {
            padding: 20px;

            .price-chart-box {
                width: 60%;
                display: none;
            }

            .price-chart {
                background: transparentize($text-color-primary, 0.9);
                position: relative;
                border-radius: 4px;
            }
        }
        .chart-box {
            position: relative;
            min-height: 50px;

            .data-range-picker {
                position: absolute;
                top: 0;
                left: 20px;
                background: transparentize($text-color-primary, 0.9);
                padding: 5px 10px;
                cursor: pointer;
                border-radius: 4px;

                &:hover {
                    background: transparentize($text-color-primary, 0.8);
                }
            }
            .peity {
                display: inherit;
            }
            .labels {
                position: absolute;
                bottom: 0;
                z-index: 1;
                left: 0;
                right: 0;
                font-size: 12px;
                padding-bottom: 5px;
                opacity: 0.6;
            }
        }
    }
}

.widget {
    height: 200px;
    position: relative;

    .widget-header {
        .widget-icon-box {
            background: rgba(0, 0, 0, 0.02);
            border: 1px solid rgba(0, 0, 0, 0.02);
            text-align: center;
            width: 60px;
            padding: 5px;
        }

        .widget-title {
            font-weight: bold;
        }
    }

    .badge-box {
        .badge {
            //background: rgba(0, 0, 0, .02);
            display: inline-block;
            //padding: 2px 5px;
            //border: 1px solid rgba(0, 0, 0, .02);
            border-radius: 4px;
            font-size: 80%;
        }
    }
}

.conversion-widget {
    .conversion-title {
        background: $text-color-primary;
        color: $background-color;
        padding: 10px 15px;
        margin: 0;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
    }

    .conversion-table {
        width: 100%;

        thead {
            th {
                opacity: 0.6;
            }
        }

        tbody {
            tr {
                td {
                    &.tokens {
                        i {
                            font-size: 20px;
                            opacity: 0.4;
                        }
                    }
                }
            }
        }
    }
}

.candle-chart-box {
    .zoom-box {
        margin-top: 5px;
        margin-bottom: 5px;

        .label {
            background: transparentize($background-color, 0.8);
            padding: 1px 5px;
            font-size: 14px;
            margin: 0 5px;

            &.selected {
                background: transparentize($text-color-accent, 0.5);
            }
        }
    }
}

/*@media (max-width: 768px) {
.el-row {
  //margin-left: 0 !important;
  //margin-right: 0 !important;

  .el-col-24 {
    //padding-left: 0 !important;
    //padding-right: 0 !important;
  }
}
}*/

@media (min-width: 1300px) {
    .wallet-box {
        .content {
            .portfolio {
                .price-chart-box {
                    display: block;
                }
            }
        }
    }
}

@media (max-width: 991px) {
    .wallet-box {
        border: none;
    }
    .candle-chart-box {
        .price-box {
            display: none;
        }
    }
}

@media (max-width: 400px) {
    .wallet-box {
        .select-wallet {
            height: 50px;

            .wallet-item {
                height: 50px;

                .icon {
                    width: 50px;
                    line-height: 50px;
                    font-size: 30px;
                }

                .coin {
                    .title {
                        font-size: 16px;

                        .cod {
                            display: none;
                        }
                    }
                    .balance {
                        display: none;
                    }
                }

                .arrow {
                    width: 50px;
                    line-height: 50px;
                    font-size: 40px;
                }
            }

            .wallet-list {
                top: 50px;
            }
        }
    }

    .conversion-widget {
        .conversion-table {
            font-size: 13px;

            tbody {
                tr {
                    td {
                        &.tokens {
                            i {
                                font-size: 14px;
                            }
                        }
                    }
                }
            }
        }
    }
}
</style>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-crypto-dashboard {
    #crypto-banner {
        margin-bottom: 0px;
        padding-top: 10px;
        padding-bottom: 40px;
        box-shadow: 0px -30px 0px 0px $background-color inset;
        //background: transparentize($text-color-primary, 0.9);
        box-sizing: border-box;

        &.marqueeInfinite {
            display: -webkit-box;
            display: -ms-flexbox;
            display: flex;
            overflow: hidden;
            white-space: nowrap;
        }

        &.marqueeInfinite > * {
            -ms-flex-negative: 0;
            flex-shrink: 0;
            width: -moz-max-content;
            -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
            will-change: transform;
        }

        &.marqueeInfinite > * > * {
            -ms-flex-negative: 0;
            flex-shrink: 0;
            display: inline-block;
        }

        ul,
        li {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        li {
            display: inline-block;
            margin-right: 30px;
            //border-bottom: 2px solid $text-color-primary;

            i {
                margin-right: 7px;
            }
        }
    }

    .wallet-box {
        .content {
            .chart-box {
                .peity {
                    display: inherit;
                }
            }
        }
    }

    .vb-content {
        padding: 0 20px;
        box-sizing: border-box !important;
        margin-top: -5px;
        margin-left: -20px;
        margin-right: -20px;
        height: calc(100% + 15px) !important;
        width: calc(100% + 40px) !important;
    }
}

@media (max-width: 768px) {
    .page-crypto-dashboard {
        .vb-content {
            padding: 0 5px !important;
            margin: -5px;
            width: calc(100% + 10px) !important;
        }
    }
}
</style>
