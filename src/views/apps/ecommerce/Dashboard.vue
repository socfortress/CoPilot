<template>
    <el-scrollbar class="page-ecommerce-dashboard">
        <resize-observer @notify="__resizeHanlder" />

        <div class="card-base card-alt">
            <el-row :gutter="30">
                <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                    <div class="widget p-20">
                        <div class="text-uppercase text-right flex">
                            <div class="box grow">
                                <h3 class="m-0">2.384</h3>
                                <p class="m-0">Daily Orders</p>
                            </div>
                            <div class="icon-box ph-15 accent-text">
                                <i class="mdi mdi-cart-outline"></i>
                            </div>
                        </div>
                        <div class="progress-box mt-10">
                            <el-progress :percentage="78" class="themed"></el-progress>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                    <div class="widget p-20">
                        <div class="text-uppercase text-right flex">
                            <div class="box grow">
                                <h3 class="m-0">7.945,87 $</h3>
                                <p class="m-0">Daily Earnings</p>
                            </div>
                            <div class="icon-box ph-15 accent-text">
                                <i class="mdi mdi-currency-usd"></i>
                            </div>
                        </div>
                        <div class="progress-box mt-10">
                            <el-progress :percentage="67" class="themed"></el-progress>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                    <div class="widget p-20">
                        <div class="text-uppercase text-right flex">
                            <div class="box grow">
                                <h3 class="m-0">5.760</h3>
                                <p class="m-0">Monthly Sales</p>
                            </div>
                            <div class="icon-box ph-15 accent-text">
                                <i class="mdi mdi-cart-outline"></i>
                            </div>
                        </div>
                        <div class="progress-box mt-10">
                            <el-progress :percentage="23" class="themed"></el-progress>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                    <div class="widget p-20">
                        <div class="text-uppercase text-right flex">
                            <div class="box grow">
                                <h3 class="m-0">68.329,29 $</h3>
                                <p class="m-0">Monthly Earnings</p>
                            </div>
                            <div class="icon-box ph-15 accent-text">
                                <i class="mdi mdi-currency-usd"></i>
                            </div>
                        </div>
                        <div class="progress-box mt-10">
                            <el-progress :percentage="37" class="themed"></el-progress>
                        </div>
                    </div>
                </el-col>
            </el-row>
        </div>

        <div class="card-base card-shadow--medium bg-white black-text ph-5 p-0 pb-20 mt-20">
            <el-row>
                <el-col :xs="24" :sm="12" :md="12" :lg="16" :xl="16">
                    <div>
                        <div id="chart" :style="{ height: '500px', width: '100%' }"></div>
                    </div>
                </el-col>
                <el-col :xs="24" :sm="12" :md="12" :lg="8" :xl="8">
                    <div>
                        <div id="pie" :style="{ height: '500px', width: '100%' }"></div>
                    </div>
                </el-col>
            </el-row>
        </div>

        <el-scrollbar class="table-box card-base card-outline mv-20">
            <table class="styled striped hover">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Customer</th>
                        <th>Location</th>
                        <th>Amount</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in gridData" :key="item.id">
                        <td>
                            <div class="item-box item-product">
                                <div class="product-image">
                                    <img :src="item.photo" />
                                </div>
                                <div>
                                    <h4 class="m-0 mb-5">{{ item.product }}</h4>
                                    <p class="m-0">{{ item.price }} $</p>
                                </div>
                            </div>
                        </td>
                        <td>
                            <div class="item-box item-customer">
                                <h4 class="m-0 mb-5">{{ item.customer }}</h4>
                                <p class="m-0">
                                    <a>{{ item.email }}</a>
                                </p>
                            </div>
                        </td>
                        <td>
                            <div class="item-box item-location">
                                <h4 class="m-0 mb-5">{{ item.address }}</h4>
                                <p class="m-0 o-060">{{ item.city }}</p>
                            </div>
                        </td>
                        <td>
                            <div class="item-box item-amount">
                                <h4 class="m-0 mb-5">{{ item.amount }} $</h4>
                                <p class="m-0 o-060">{{ item.qnt }}</p>
                            </div>
                        </td>
                        <td>
                            <div :class="'item-box item-status status-' + item.status">
                                <h4 class="m-0 mb-5">{{ item.status }}</h4>
                                <p class="m-0 o-060">{{ item.date }}</p>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </el-scrollbar>
    </el-scrollbar>
</template>

<script>
import * as echarts from "echarts"
import Chance from "chance"
const chance = new Chance()
import _ from "lodash"
import ResizeObserver from "@/components/vue-resize/ResizeObserver.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "EcommerceDashboard",
    data() {
        return {
            chart: null,
            pie: null,
            gridData: []
        }
    },
    created() {
        this.initGridData()
    },
    mounted() {
        this.initChart()
        this.initPie()
        window.addEventListener("resize", this.__resizeHanlder)
    },
    beforeUnmount() {
        if (!this.chart) {
            return
        }

        if (!this.pie) {
            return
        }

        window.removeEventListener("resize", this.__resizeHanlder)
        this.chart.dispose()
        this.pie.dispose()
        this.chart = null
        this.pie = null
    },
    methods: {
        __resizeHanlder: _.throttle(function (e) {
            if (this.chart) {
                // this.chart.resize()
                this.chart.dispose()
                this.initChart()
            }
            if (this.pie) {
                this.pie.resize()
            }
        }, 700),
        initChart() {
            this.chart = echarts.init(document.getElementById("chart"))
            this.chart.setOption({
                //backgroundColor: '#394056',
                title: {
                    top: 20,
                    text: "SALES STATISTICS",
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
                        data: [
                            "13:00",
                            "13:05",
                            "13:10",
                            "13:15",
                            "13:20",
                            "13:25",
                            "13:30",
                            "13:35",
                            "13:40",
                            "13:45",
                            "13:50",
                            "13:55"
                        ]
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
                        name: "Product-A",
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
                        data: [220, 182, 191, 134, 150, 120, 110, 125, 145, 122, 165, 122]
                    },
                    {
                        name: "Product-B",
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
                        data: [120, 110, 125, 145, 122, 165, 122, 220, 182, 191, 134, 150]
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
            this.pie = echarts.init(document.getElementById("pie"))
            this.pie.setOption({
                title: {
                    top: 20,
                    text: "ORDER STATUS",
                    textStyle: { fontWeight: "normal", fontSize: 16, fontFamily: "Nunito Sans" /*color: '#F1F1F3'*/ },
                    left: "1%"
                },
                tooltip: {
                    trigger: "item",
                    formatter: "{a} <br/>{b}: {c} ({d}%)"
                },
                series: [
                    {
                        name: "Status",
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
                                value: 335,
                                name: "Orders",
                                selected: true,
                                itemStyle: { color: "rgb(95, 143, 223)" }
                            },
                            { value: 679, name: "Pending", itemStyle: { color: "rgb(19, 206, 102)" } },
                            { value: 1548, name: "Delivered", itemStyle: { color: "rgb(247, 186, 43)" } }
                        ]
                    },
                    {
                        name: "Products",
                        type: "pie",
                        radius: ["45%", "60%"],

                        data: [
                            { value: 335, name: "p1", itemStyle: { color: "#3f84f6" } },
                            { value: 310, name: "p2", itemStyle: { color: "#4c8bf7" } },
                            { value: 234, name: "p3", itemStyle: { color: "#5a95f7" } },
                            { value: 135, name: "p4", itemStyle: { color: "#70a3f8" } },
                            { value: 1048, name: "p5", itemStyle: { color: "#8ab4fa" } },
                            { value: 251, name: "p6", itemStyle: { color: "#a3c4fb" } },
                            { value: 147, name: "p7", itemStyle: { color: "#bfd6fc" } },
                            { value: 102, name: "p8", itemStyle: { color: "#d4e4fd" } }
                        ],

                        itemStyle: {
                            color: "rgb(19, 206, 102)"
                        }
                    }
                ]
            })
        },
        initGridData() {
            const year = new Date().getFullYear()
            const status_list = ["Complete", "Pending", "Returned", "Paid"]

            _.times(10, number => {
                let price = chance.floating({ min: 1, max: 100, fixed: 2 })
                let qnt = chance.integer({ min: 1, max: 5 })
                let amount = price * qnt

                this.gridData.push({
                    customer: chance.name(),
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    city: chance.city(),
                    address: chance.address(),
                    email: chance.email(),
                    product: chance.sentence({ words: 3 }),
                    price: _.replace(price.toFixed(2).toString(), ".", ","),
                    qnt,
                    amount: _.replace(amount.toFixed(2).toString(), ".", ","),
                    status: status_list[chance.integer({ min: 0, max: 3 })],
                    date: chance.date({ string: true, year: year }),
                    id: number
                })
            })
        }
    },
    components: { ResizeObserver }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-ecommerce-dashboard {
    .widget {
        .icon-box {
            font-size: 30px;
        }
    }

    .table-box {
        .item-box {
            &.item-product {
                .product-image {
                    width: 50px;
                    margin-right: 15px;
                    float: left;

                    img {
                        width: 100%;
                    }
                }
            }

            &.item-status {
                padding: 5px 10px;

                &.status- {
                    &Complete {
                        background: rgba(44, 196, 120, 0.25);
                    }
                    &Pending {
                        background: rgba(247, 186, 42, 0.25);
                    }
                    &Returned {
                        background: rgba(243, 24, 71, 0.25);
                    }
                    &Paid {
                        background: rgba(45, 109, 211, 0.25);
                    }
                }
            }
        }
    }
}
</style>
