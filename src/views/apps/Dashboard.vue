<template>
    <el-scrollbar class="page-dashboard">
        <resize-observer @notify="__resizeHanlder" />

        <el-row class="mt-0" :gutter="30">
            <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                <div class="card-base card-shadow--medium mb-30 widget small-widget" v-loading="!asyncComponent">
                    <div class="widget-hdr ph-20 pt-20">
                        <div class="flex justify-center align-center">
                            <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                                <i class="widget-icon mdi mdi-account-multiple accent-text fs-30"></i>
                                <div class="badge-box">
                                    <span class="badge">
                                        <i class="mdi mdi-trending-up success-text mr-10"></i>
                                        <strong class="accent-text">16%</strong>
                                    </span>
                                </div>
                            </div>
                            <div class="widget-info box grow text-truncate animate__animated animate__fadeInLeft">
                                <div class="o-050 widget-title text-truncate pt-5 pb-10">Users</div>
                                <h2 class="m-0 text-truncate">4,523</h2>
                            </div>
                        </div>
                    </div>

                    <component
                        :is="asyncComponent"
                        :type="'line'"
                        :options="{ width: '100%', height: 80 }"
                        :data="[1, 3, 2, 4, 4, 9, 3, 4, 6, 5, 4, 6, 9, 8, 11, 12, 13, 12, 12, 14].toString()"
                    />
                </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                <div class="card-base card-shadow--medium mb-30 widget small-widget" v-loading="!asyncComponent">
                    <div class="widget-hdr ph-20 pt-20">
                        <div class="flex justify-center align-center">
                            <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                                <i class="widget-icon mdi mdi-eye accent-text fs-30"></i>
                                <div class="badge-box">
                                    <span class="badge">
                                        <i class="mdi mdi-trending-up success-text mr-10"></i>
                                        <strong class="accent-text">11%</strong>
                                    </span>
                                </div>
                            </div>
                            <div class="widget-info box grow text-truncate animate__animated animate__fadeInLeft">
                                <div class="o-050 widget-title text-truncate pt-5 pb-10">Views</div>
                                <h2 class="m-0 text-truncate">2,523</h2>
                            </div>
                        </div>
                    </div>

                    <component
                        :is="asyncComponent"
                        :type="'bar'"
                        :options="{ width: '100%', height: 80, fill: ['#c6d9fd'] }"
                        :data="[1, 3, 2, 4, 4, 9, 3, 4, 6, 5, 4, 6, 9, 8, 7, 6, 5, 12, 10, 9].toString()"
                    />
                </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                <div class="card-base card-shadow--medium mb-30 widget small-widget" v-loading="!asyncComponent">
                    <div class="widget-hdr ph-20 pt-20">
                        <div class="flex justify-center align-center">
                            <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                                <i class="widget-icon mdi mdi-account-convert success-text fs-30"></i>
                                <div class="badge-box">
                                    <span class="badge">
                                        <i class="mdi mdi-trending-neutral info-text mr-10"></i>
                                        <strong class="success-text">1%</strong>
                                    </span>
                                </div>
                            </div>
                            <div class="widget-info box grow text-truncate animate__animated animate__fadeInLeft">
                                <div class="o-050 widget-title text-truncate pt-5 pb-10">Conversion</div>
                                <h2 class="m-0 text-truncate">9,832</h2>
                            </div>
                        </div>
                    </div>

                    <component
                        :is="asyncComponent"
                        :type="'line'"
                        :options="{ width: '100%', height: 80, fill: '#56f19a', stroke: '#67C23A' }"
                        :data="[10, 7, 8, 5, 4, 9, 3, 4, 6, 5, 4, 4, 2, 4, 5, 9, 13, 12, 12, 14].toString()"
                    />
                </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                <div class="card-base card-shadow--medium mb-30 widget small-widget" v-loading="!asyncComponent">
                    <div class="widget-hdr ph-20 pt-20">
                        <div class="flex justify-center align-center">
                            <div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
                                <i class="widget-icon mdi mdi-cash-multiple success-text fs-30"></i>
                                <div class="badge-box">
                                    <span class="badge">
                                        <i class="mdi mdi-trending-neutral info-text mr-10"></i>
                                        <strong class="success-text">0%</strong>
                                    </span>
                                </div>
                            </div>
                            <div class="widget-info box grow text-truncate animate__animated animate__fadeInLeft">
                                <div class="o-050 widget-title text-truncate pt-5 pb-10">Revenue</div>
                                <h2 class="m-0 text-truncate">6,364</h2>
                            </div>
                        </div>
                    </div>

                    <component
                        :is="asyncComponent"
                        :type="'bar'"
                        :options="{ width: '100%', height: 80, fill: ['#56f19a'] }"
                        :data="[6, 5, 4, 3, 5, 3, 4, 5, 6, 5, 4, 2, 3, 8, 7, 6, 5, 2, 1, 5].toString()"
                    />
                </div>
            </el-col>
            <!--<el-col :xs="24" :sm="12" :md="8" :lg="4" :xl="4">
				<div class="card-base card-shadow--medium mb-30 widget small-widget" v-loading="!asyncComponent">

					<div class="widget-hdr ph-20 pt-20">
						<div class="flex justify-center align-center">
							<div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
								<i class="widget-icon mdi mdi-message-text-outline danger-text fs-30"></i>
								<div class="badge-box">
									<span class="badge"><i class="mdi mdi-trending-down danger-text mr-10"></i><strong class="danger-text">23%</strong></span>
								</div>
							</div>
							<div class="widget-info box grow text-truncate animate__animated animate__fadeInLeft">
								<div class="o-050 widget-title text-truncate pt-5 pb-10">Messages</div>
								<h2 class="m-0 text-truncate">52,628</h2>
							</div>
						</div>
					</div>

					<component :is="asyncComponent" :type="'line'" :options='{ width: "100%", height: 80, fill: "#EF5F8B", stroke: "#CF2256" }' :data="[9, 7, 5, 4, 4, 8, 3, 4, 6, 5, 4, 6, 5, 7, 3, 2, 4, 3, 2, 1].toString()"/>
				</div>
			</el-col>
			<el-col :xs="24" :sm="12" :md="8" :lg="4" :xl="4">
				<div class="card-base card-shadow--medium mb-30 widget small-widget" v-loading="!asyncComponent">

					<div class="widget-hdr ph-20 pt-20">
						<div class="flex justify-center align-center">
							<div class="widget-icon-box mr-20 animate__animated animate__fadeInRight">
								<i class="widget-icon mdi mdi-cart danger-text fs-30"></i>
								<div class="badge-box">
									<span class="badge"><i class="mdi mdi-trending-down danger-text mr-10"></i><strong class="danger-text">9%</strong></span>
								</div>
							</div>
							<div class="widget-info box grow text-truncate animate__animated animate__fadeInLeft">
								<div class="o-050 widget-title text-truncate pt-5 pb-10">Purchases</div>
								<h2 class="m-0 text-truncate">3,346</h2>
							</div>
						</div>
					</div>

					<component :is="asyncComponent" :type="'bar'" :options='{ width: "100%", height: 80, fill: ["#EF5F8B"] }' :data="[1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4].toString()"/>
				</div>
			</el-col>-->
        </el-row>

        <el-row class="mt-0" :gutter="30">
            <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
                <div
                    class="card-base card-shadow--medium bg-accent p-20"
                    style="height: 400px"
                    v-loading="!asyncChart1"
                >
                    <h1 class="white-text mv-0 animate__animated animate__fadeInDown">Statistics</h1>
                    <h3 class="mt-0 mb-40 white-text o-050 animate__animated animate__slideInUp">revenue</h3>
                    <div id="chart1" style="height: 300px; width: 100%"></div>
                </div>
            </el-col>
        </el-row>

        <el-row class="mt-30" :gutter="30">
            <el-col :xs="24" :sm="12" :md="14" :lg="16" :xl="18">
                <div class="card-base card-shadow--medium mb-30" style="height: 410px">
                    <div class="p-20 flex justify-space-between">
                        <div>
                            <h2 class="mv-0 animate__animated animate__fadeInDown">Progress</h2>
                            <h4 class="mt-5 mb-0 o-050 animate__animated animate__slideInUp">This month</h4>
                        </div>
                        <div class="radio-switcher">
                            <el-radio-group v-model="radio1">
                                <el-radio-button label="Day"></el-radio-button>
                                <el-radio-button label="Week"></el-radio-button>
                                <el-radio-button label="Month"></el-radio-button>
                            </el-radio-group>
                        </div>
                    </div>
                    <el-scrollbar>
                        <table class="styled striped">
                            <thead>
                                <tr>
                                    <th></th>
                                    <th style="min-width: 85px">First name</th>
                                    <th style="min-width: 80px">Last name</th>
                                    <th style="min-width: 130px">Activity</th>
                                    <th style="min-width: 195px">Progress</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item of list" :key="item.id">
                                    <td class="text-right">
                                        <span
                                            class="status-indicator ml-10 pulse"
                                            :class="{
                                                active: item.status === 'active',
                                                positive: item.status === 'positive',
                                                intermediary: item.status === 'intermediary',
                                                negative: item.status === 'negative'
                                            }"
                                        ></span>
                                    </td>
                                    <td style="min-width: 80px">{{ item.first_name }}</td>
                                    <td style="min-width: 80px">{{ item.last_name }}</td>
                                    <td style="min-width: 130px">
                                        <peity
                                            :options="{ fill: ['#a4bbe0', '#5f8fdf'] }"
                                            :type="'donut'"
                                            :data="'1/5'"
                                        ></peity>
                                        <peity
                                            :options="{ fill: ['#a4bbe0', '#5f8fdf'] }"
                                            :type="'donut'"
                                            :data="'226/360'"
                                        ></peity>
                                        <peity
                                            :options="{ fill: ['#a4bbe0', '#5f8fdf'] }"
                                            :type="'donut'"
                                            :data="'0.52/1.561'"
                                        ></peity>
                                        <peity
                                            :options="{ fill: ['#a4bbe0', '#5f8fdf'] }"
                                            :type="'donut'"
                                            :data="'0.52/1.561'"
                                        ></peity>
                                        <peity
                                            :options="{ fill: ['#a4bbe0', '#5f8fdf'] }"
                                            :type="'donut'"
                                            :data="'0.52/1.561'"
                                        ></peity>
                                    </td>
                                    <td style="min-width: 195px">
                                        <el-progress
                                            :percentage="item.progress"
                                            :status="item.status === 'positive' ? 'success' : null"
                                            :color="
                                                item.status === 'negative'
                                                    ? '#ff4d4d'
                                                    : item.status === 'intermediary'
                                                    ? '#ffaa00'
                                                    : ''
                                            "
                                        ></el-progress>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </el-scrollbar>
                </div>
            </el-col>
            <el-col :xs="24" :sm="12" :md="10" :lg="8" :xl="6">
                <div
                    class="card-base card-shadow--medium mb-30 bg-primary p-20"
                    style="height: 410px; box-sizing: border-box"
                    v-loading="!asyncChart2"
                >
                    <div id="chart2" style="height: 350px; width: 80%; margin-left: 10%"></div>
                </div>
            </el-col>
        </el-row>

        <el-row class="mt-0" :gutter="30">
            <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
                <div class="card-base card-shadow--medium p-20 mb-30" style="height: 295px">
                    <div class="flex justify-space-between">
                        <div>
                            <h2 class="mv-0 animate__animated animate__fadeInDown">Report</h2>
                            <h4 class="mt-5 mb-40 o-050 animate__animated animate__slideInUp">This week</h4>
                        </div>
                        <div class="radio-switcher">
                            <el-radio-group v-model="radio2">
                                <el-radio-button label="Day"></el-radio-button>
                                <el-radio-button label="Week"></el-radio-button>
                                <el-radio-button label="Month"></el-radio-button>
                            </el-radio-group>
                        </div>
                    </div>

                    <h4 class="mb-0 mt-0">New Users</h4>
                    <el-progress :percentage="100" status="success"></el-progress>
                    <h4 class="mb-0">Views</h4>
                    <el-progress :percentage="70"></el-progress>
                    <h4 class="mb-0">Conversions</h4>
                    <el-progress :percentage="20" status="exception"></el-progress>
                </div>
            </el-col>
        </el-row>
    </el-scrollbar>
</template>

<script>
import _ from "lodash"
import * as echarts from "echarts"
import Peity from "../../components/vue-peity/Peity.vue"
import ResizeObserver from "../../components/vue-resize/ResizeObserver.vue"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Dashboard",
    data() {
        return {
            asyncComponent: "peity",
            asyncChart1: true,
            asyncChart2: true,
            chart1: null,
            chart2: null,
            resized: false,
            list: [
                {
                    activity: 111,
                    progress: 70,
                    status: "active",
                    id: 1,
                    first_name: "Fidela",
                    last_name: "MacLaverty",
                    email: "fmaclaverty0@scribd.com",
                    gender: "Female",
                    ip_address: "165.9.197.163"
                },
                {
                    activity: 111,
                    progress: 55,
                    status: "intermediary",
                    id: 2,
                    first_name: "Garrard",
                    last_name: "Inge",
                    email: "ginge1@51.la",
                    gender: "Male",
                    ip_address: "138.87.225.97"
                },
                {
                    activity: 111,
                    progress: 100,
                    status: "positive",
                    id: 3,
                    first_name: "Clayborn",
                    last_name: "Blencoe",
                    email: "cblencoe2@cbc.ca",
                    gender: "Male",
                    ip_address: "237.146.154.222"
                },
                {
                    activity: 111,
                    progress: 12,
                    status: "negative",
                    id: 6,
                    first_name: "Elna",
                    last_name: "Deboick",
                    email: "edeboick5@4shared.com",
                    gender: "Female",
                    ip_address: "53.209.210.199"
                },
                {
                    activity: 111,
                    progress: 0,
                    status: "",
                    id: 8,
                    first_name: "Sheffie",
                    last_name: "Fellgett",
                    email: "sfellgett7@ow.ly",
                    gender: "Male",
                    ip_address: "219.29.191.217"
                }
                //{"activity":111, "progress": 68, "status":"active", "id":4,"first_name":"Reinaldos","last_name":"Briiginshaw","email":"rbriiginshaw3@mashable.com","gender":"Male","ip_address":"35.148.222.21"},
                //{"activity":111, "progress": 43, "status":"intermediary", "id":5,"first_name":"Abigael","last_name":"Richmond","email":"arichmond4@shinystat.com","gender":"Female","ip_address":"135.221.192.85"},
                //{"activity":111, "progress": 100, "status":"positive", "id":7,"first_name":"Lanna","last_name":"Prentice","email":"lprentice6@oracle.com","gender":"Female","ip_address":"198.34.29.215"},
                //{"activity":111, "progress": 88, "status":"active", "id":9,"first_name":"Mamie","last_name":"Calkin","email":"mcalkin8@oakley.com","gender":"Female","ip_address":"69.0.235.44"},
                //{"activity":111, "progress": 9, "status":"negative", "id":10,"first_name":"Saudra","last_name":"Dunniom","email":"sdunniom9@ameblo.jp","gender":"Female","ip_address":"182.157.218.101"}
            ],
            radio1: "Month",
            radio2: "Week",
            data3: {
                labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
                datasets: [
                    {
                        label: "Visitors",
                        backgroundColor: "#fff",
                        stack: "Stack 0",
                        data: [23, 41, 34, 62, 46, 57, 68]
                    }
                ]
            },
            options3: {
                maintainAspectRatio: false,
                title: {
                    display: false,
                    text: "Chart.js Bar Chart - Stacked"
                },
                legend: {
                    display: false
                },
                tooltips: {
                    mode: "index",
                    intersect: false
                },
                responsive: true,
                scales: {
                    xAxes: [
                        {
                            stacked: true,
                            gridLines: {
                                display: false,
                                drawBorder: false
                            },
                            ticks: {
                                fontColor: "#fff"
                            }
                        }
                    ],
                    yAxes: [
                        {
                            stacked: true,
                            gridLines: {
                                display: false,
                                drawBorder: false
                            },
                            ticks: {
                                display: false
                            }
                        }
                    ]
                }
            }
        }
    },
    computed: {
        smallWidget() {
            return this.dashboardWidth >= 970 && this.dashboardWidth <= 1412 && this.windowWidth >= 1200
        }
    },
    methods: {
        __resizeHanlder: _.throttle(function (e) {
            if (this.resized) {
                this.asyncComponent = null
                this.removePeity()
                setTimeout(() => {
                    this.asyncComponent = "peity"
                }, 1000)

                this.asyncChart1 = false
                this.asyncChart2 = false
                setTimeout(() => {
                    this.asyncChart1 = true
                    this.resizeChart1()
                }, 1000)
                setTimeout(() => {
                    this.asyncChart2 = true
                    this.resizeChart2()
                }, 2500)
            }
            this.resized = true
        }, 700),
        removePeity() {
            const peityEl = document.querySelectorAll(".widget .peity") //.forEach((el)=>{el.remove()})
            //ie fix
            for (let i = 0; i < peityEl.length; i++) {
                peityEl[i].parentNode.removeChild(peityEl[i])
            }
        },
        initChart1() {
            this.chart1 = echarts.init(document.getElementById("chart1"))

            // Generate data
            let category = []
            let dottedBase = +new Date()
            let lineData = []
            let barData = []

            for (let i = 0; i < 6; i++) {
                let date = new Date((dottedBase += 3600 * 24 * 1000))
                category.push([date.getFullYear(), date.getMonth() + 1, date.getDate()].join("-"))
                let b = Math.random() * 200
                let d = Math.random() * 200
                barData.push(parseInt(b))
                lineData.push(parseInt(d + b))
            }

            this.chart1.setOption({
                //backgroundColor: '#0f375f',
                coordinateSystem: {},
                grid: {
                    show: false,
                    left: "20px",
                    right: "50px",
                    bottom: "20px",
                    top: "20px",
                    containLabel: true
                },
                tooltip: {
                    trigger: "axis",
                    axisPointer: {
                        type: "cross"
                    }
                },
                legend: {
                    show: false,
                    data: ["line", "bar"],
                    textStyle: {
                        color: "#ccc"
                    }
                },
                xAxis: {
                    data: category,
                    boundaryGap: false,
                    axisLine: {
                        lineStyle: {
                            color: "rgba(255,255,255,0.5)"
                        }
                    }
                },
                yAxis: {
                    splitLine: { show: false },
                    axisLine: {
                        lineStyle: {
                            color: "rgba(255,255,255,0.5)"
                        }
                    }
                },
                series: [
                    {
                        name: "Data A",
                        type: "line",
                        smooth: true,
                        showAllSymbol: true,
                        symbol: "emptyCircle",
                        symbolSize: 10,
                        lineStyle: {
                            color: "#fff"
                        },
                        itemStyle: {
                            color: "#fff",
                            borderColor: "#5f8fdf",
                            borderWidth: 3
                        },
                        areaStyle: {
                            color: "rgba(255,255,255,0.2)"
                        },
                        animationDuration: 2800,
                        animationEasing: "cubicInOut",
                        data: lineData
                    },
                    {
                        name: "Data B",
                        type: "bar",
                        barWidth: 10,
                        itemStyle: {
                            borderRadius: 5,
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: "#fff" },
                                { offset: 1, color: "rgba(255,255,255,0)" }
                            ])
                        },
                        data: barData
                    },
                    /* {
						name: 'line',
						type: 'bar',
						barGap: '-100%',
						barWidth: 10,
						itemStyle: {

							color: new echarts.graphic.LinearGradient(
									0, 0, 0, 1,
									[
										{offset: 0, color: 'rgba(20,200,212,0.5)'},
										{offset: 0.2, color: 'rgba(20,200,212,0.2)'},
										{offset: 1, color: 'rgba(20,200,212,0)'}
									]
							)
						},
						z: -12,
						data: lineData
					},*/

                    {
                        name: "Data C",
                        type: "pictorialBar",
                        symbol: "rect",
                        itemStyle: {
                            color: "rgba(255,255,255,0.1)"
                        },
                        symbolRepeat: true,
                        symbolSize: [12, 4],
                        symbolMargin: 1,
                        z: -10,
                        data: lineData
                    }
                ]
            })
        },
        initChart2() {
            this.chart2 = echarts.init(document.getElementById("chart2"))

            var dataBJ = [
                [55, 9, 56, 0.46, 18, 6, 1],
                [25, 11, 21, 0.65, 34, 9, 2],
                [56, 7, 63, 0.3, 14, 5, 3],
                [33, 7, 29, 0.33, 16, 6, 4],
                [42, 24, 44, 0.76, 40, 16, 5],
                [82, 58, 90, 1.77, 68, 33, 6],
                [74, 49, 77, 1.46, 48, 27, 7],
                [78, 55, 80, 1.29, 59, 29, 8],
                [267, 216, 280, 4.8, 108, 64, 9],
                [185, 127, 216, 2.52, 61, 27, 10],
                [39, 19, 38, 0.57, 31, 15, 11],
                [41, 11, 40, 0.43, 21, 7, 12],
                [64, 38, 74, 1.04, 46, 22, 13],
                [108, 79, 120, 1.7, 75, 41, 14],
                [108, 63, 116, 1.48, 44, 26, 15],
                [33, 6, 29, 0.34, 13, 5, 16],
                [94, 66, 110, 1.54, 62, 31, 17],
                [186, 142, 192, 3.88, 93, 79, 18],
                [57, 31, 54, 0.96, 32, 14, 19],
                [22, 8, 17, 0.48, 23, 10, 20],
                [39, 15, 36, 0.61, 29, 13, 21],
                [94, 69, 114, 2.08, 73, 39, 22],
                [99, 73, 110, 2.43, 76, 48, 23],
                [31, 12, 30, 0.5, 32, 16, 24],
                [42, 27, 43, 1, 53, 22, 25],
                [154, 117, 157, 3.05, 92, 58, 26],
                [234, 185, 230, 4.09, 123, 69, 27],
                [160, 120, 186, 2.77, 91, 50, 28],
                [134, 96, 165, 2.76, 83, 41, 29],
                [52, 24, 60, 1.03, 50, 21, 30],
                [46, 5, 49, 0.28, 10, 6, 31]
            ]

            var dataGZ = [
                [26, 37, 27, 1.163, 27, 13, 1],
                [85, 62, 71, 1.195, 60, 8, 2],
                [78, 38, 74, 1.363, 37, 7, 3],
                [21, 21, 36, 0.634, 40, 9, 4],
                [41, 42, 46, 0.915, 81, 13, 5],
                [56, 52, 69, 1.067, 92, 16, 6],
                [64, 30, 28, 0.924, 51, 2, 7],
                [55, 48, 74, 1.236, 75, 26, 8],
                [76, 85, 113, 1.237, 114, 27, 9],
                [91, 81, 104, 1.041, 56, 40, 10],
                [84, 39, 60, 0.964, 25, 11, 11],
                [64, 51, 101, 0.862, 58, 23, 12],
                [70, 69, 120, 1.198, 65, 36, 13],
                [77, 105, 178, 2.549, 64, 16, 14],
                [109, 68, 87, 0.996, 74, 29, 15],
                [73, 68, 97, 0.905, 51, 34, 16],
                [54, 27, 47, 0.592, 53, 12, 17],
                [51, 61, 97, 0.811, 65, 19, 18],
                [91, 71, 121, 1.374, 43, 18, 19],
                [73, 102, 182, 2.787, 44, 19, 20],
                [73, 50, 76, 0.717, 31, 20, 21],
                [84, 94, 140, 2.238, 68, 18, 22],
                [93, 77, 104, 1.165, 53, 7, 23],
                [99, 130, 227, 3.97, 55, 15, 24],
                [146, 84, 139, 1.094, 40, 17, 25],
                [113, 108, 137, 1.481, 48, 15, 26],
                [81, 48, 62, 1.619, 26, 3, 27],
                [56, 48, 68, 1.336, 37, 9, 28],
                [82, 92, 174, 3.29, 0, 13, 29],
                [106, 116, 188, 3.628, 101, 16, 30],
                [118, 50, 0, 1.383, 76, 11, 31]
            ]

            var dataSH = [
                [91, 45, 125, 0.82, 34, 23, 1],
                [65, 27, 78, 0.86, 45, 29, 2],
                [83, 60, 84, 1.09, 73, 27, 3],
                [109, 81, 121, 1.28, 68, 51, 4],
                [106, 77, 114, 1.07, 55, 51, 5],
                [109, 81, 121, 1.28, 68, 51, 6],
                [106, 77, 114, 1.07, 55, 51, 7],
                [89, 65, 78, 0.86, 51, 26, 8],
                [53, 33, 47, 0.64, 50, 17, 9],
                [80, 55, 80, 1.01, 75, 24, 10],
                [117, 81, 124, 1.03, 45, 24, 11],
                [99, 71, 142, 1.1, 62, 42, 12],
                [95, 69, 130, 1.28, 74, 50, 13],
                [116, 87, 131, 1.47, 84, 40, 14],
                [108, 80, 121, 1.3, 85, 37, 15],
                [134, 83, 167, 1.16, 57, 43, 16],
                [79, 43, 107, 1.05, 59, 37, 17],
                [71, 46, 89, 0.86, 64, 25, 18],
                [97, 71, 113, 1.17, 88, 31, 19],
                [84, 57, 91, 0.85, 55, 31, 20],
                [87, 63, 101, 0.9, 56, 41, 21],
                [104, 77, 119, 1.09, 73, 48, 22],
                [87, 62, 100, 1, 72, 28, 23],
                [168, 128, 172, 1.49, 97, 56, 24],
                [65, 45, 51, 0.74, 39, 17, 25],
                [39, 24, 38, 0.61, 47, 17, 26],
                [39, 24, 39, 0.59, 50, 19, 27],
                [93, 68, 96, 1.05, 79, 29, 28],
                [188, 143, 197, 1.66, 99, 51, 29],
                [174, 131, 174, 1.55, 108, 50, 30],
                [187, 143, 201, 1.39, 89, 53, 31]
            ]

            var lineStyle = {
                width: 1,
                opacity: 0.5
            }

            this.chart2.setOption({
                legend: {
                    bottom: 0,
                    data: ["Data 1", "Data 2"],
                    itemGap: 20,
                    textStyle: {
                        color: "#fff",
                        fontSize: 14
                    },
                    selectedMode: "single"
                },
                grid: {
                    height: "350px"
                },
                /*visualMap: {
				    show: true,
				    min: 0,
				    max: 20,
				    dimension: 6,
				    inRange: {
				        colorLightness: [0.5, 0.8]
				    }
				},*/
                radar: {
                    indicator: [
                        { name: "AQI", max: 250 },
                        { name: "PM2.5", max: 250 },
                        { name: "PM10", max: 250 },
                        { name: "CO", max: 5 },
                        { name: "NO2", max: 100 },
                        { name: "SO2", max: 100 }
                    ],
                    shape: "circle",
                    radius: "60%",
                    splitNumber: 5,
                    axisName: {
                        color: "rgb(238, 197, 102)"
                    },
                    splitLine: {
                        lineStyle: {
                            color: [
                                "rgba(238, 197, 102, 0.1)",
                                "rgba(238, 197, 102, 0.2)",
                                "rgba(238, 197, 102, 0.4)",
                                "rgba(238, 197, 102, 0.6)",
                                "rgba(238, 197, 102, 0.8)",
                                "rgba(238, 197, 102, 1)"
                            ].reverse()
                        }
                    },
                    splitArea: {
                        show: false
                    },
                    axisLine: {
                        lineStyle: {
                            color: "rgba(238, 197, 102, 0.5)"
                        }
                    }
                },
                series: [
                    {
                        name: "Data 1",
                        type: "radar",
                        lineStyle: lineStyle,
                        data: dataBJ,
                        symbol: "none",
                        itemStyle: {
                            color: "#F9713C"
                        },
                        areaStyle: {
                            opacity: 0.1
                        }
                    },
                    {
                        name: "Data 2",
                        type: "radar",
                        lineStyle: lineStyle,
                        data: dataSH,
                        symbol: "none",
                        itemStyle: {
                            color: "#B3E4A1"
                        },
                        areaStyle: {
                            opacity: 0.05
                        }
                    }
                    /*{
						name: 'Data 3',
						type: 'radar',
						lineStyle: lineStyle,
						data: dataGZ,
						symbol: 'none',
						itemStyle: {

							color: 'rgb(238, 197, 102)'

						},
						areaStyle: {

							opacity: 0.05

						}
					}*/
                ]
            })
        },
        destroyChart1() {
            if (this.chart1) {
                this.chart1.dispose()
                this.chart1 = null
            }
        },
        destroyChart2() {
            if (this.chart2) {
                this.chart2.dispose()
                this.chart2 = null
            }
        },
        resizeChart1() {
            if (this.chart1) {
                this.destroyChart1()
                this.initChart1()
                //this.chart1.resize()
            }
        },
        resizeChart2() {
            if (this.chart2) {
                this.chart2.resize()
            }
        }
    },
    mounted() {
        this.initChart1()
        this.initChart2()
    },
    beforeUnmount() {
        this.destroyChart1()
        this.destroyChart2()
    },
    components: { Peity, ResizeObserver }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.widget {
    height: 200px;
    position: relative;

    .widget-hdr {
        .widget-icon-box {
            background: rgba(0, 0, 0, 0.02);
            border: 1px solid rgba(0, 0, 0, 0.02);
            border-radius: 4px;
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

/*@media (min-width: 1200px) and (max-width: 1850px) {
	.widget {
		.widget-hdr {
			.widget-icon-box {
				display: none;
			}
		}
	}
}*/
@media (min-width: 768px) and (max-width: 1040px) {
    .radio-switcher {
        display: none;
    }

    .widget {
        .widget-hdr {
            .widget-icon-box {
                display: none;
            }
        }
    }
}
@media (max-width: 420px) {
    .radio-switcher {
        display: none;
    }
}
</style>

<style lang="scss">
.page-dashboard {
    .widget {
        .peity {
            position: absolute;
            bottom: -1px;
            left: 0;
            border-bottom-left-radius: 5px;
            border-bottom-right-radius: 5px;
        }
    }
    table.styled {
        .peity {
            margin-right: 10px;
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
    .page-dashboard {
        .vb-content {
            padding: 0 5px !important;
            margin: -5px;
            width: calc(100% + 10px) !important;
        }
    }
}
</style>
