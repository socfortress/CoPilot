<template>
    <el-scrollbar class="page-crypto-dashboard">
        <resize-observer @notify="__resizeHanlder" />

        <div id="crypto-banner" class="card-base">
            <ul>
                <li v-for="c in cryptocoins" :key="c.ico" :data-balloon="c.name" data-balloon-pos="down">
                    <i :class="'cc ' + c.ico"></i>{{ c.price }}
                </li>
            </ul>
        </div>

        <div class="card-base card-outline">
            <el-row class="mt-0">
                <el-col :xs="24" :sm="24" :md="12" :lg="14" :xl="14">
                    <div class="wallet-box flex column">
                        <div class="select-wallet" :class="{ open: selectWalletOpen }">
                            <div class="wallet-item selected flex">
                                <div class="icon flex column center">
                                    <i class="cc BTC"></i>
                                </div>
                                <div class="coin box grow flex column justify-center">
                                    <div class="fs-18 title">
                                        <span class="mr-10">Bitcoin Wallet</span><span class="o-050 cod">BTC</span>
                                    </div>
                                    <div class="fs-14 balance">
                                        <span class="o-070 mr-10">balance</span>
                                        <span class="accent-text">$ 9404,46</span>
                                    </div>
                                </div>
                                <div class="arrow flex column center" @click="selectWalletOpen = !selectWalletOpen">
                                    <i class="mdi mdi-chevron-down"></i>
                                </div>
                            </div>
                            <div class="wallet-list">
                                <div class="wallet-item flex">
                                    <div class="icon flex column center">
                                        <i class="cc XLM"></i>
                                    </div>
                                    <div class="coin box grow flex column justify-center">
                                        <div class="fs-18 title">
                                            <span class="mr-10">Stellar Wallet</span>
                                            <span class="o-050 cod">XLM</span>
                                        </div>
                                        <div class="fs-14 balance">
                                            <span class="o-070 mr-10">balance</span>
                                            <span class="accent-text">$ 7647,43</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="wallet-item flex">
                                    <div class="icon flex column center">
                                        <i class="cc LTC"></i>
                                    </div>
                                    <div class="coin box grow flex column justify-center">
                                        <div class="fs-18 title">
                                            <span class="mr-10">Litecoin Wallet</span>
                                            <span class="o-050 cod">LTC</span>
                                        </div>
                                        <div class="fs-14 balance">
                                            <span class="o-070 mr-10">balance</span>
                                            <span class="accent-text">$ 247,37</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="wallet-item flex">
                                    <div class="icon flex column center">
                                        <i class="mdi mdi-plus-circle"></i>
                                    </div>
                                    <div class="coin box grow flex column justify-center">
                                        <div class="fs-18 title">
                                            <span class="mr-10">Add Wallet</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="content flex column box grow">
                            <div class="portfolio box grow flex">
                                <div class="balance box grow">
                                    <h4 class="m-0 o-050">BALANCE</h4>
                                    <h1 class="m-0 mt-20 mb-10">$ 9404,46</h1>
                                    <h2 class="m-0 o-070"><i class="cc BTC-alt mr-10"></i>12</h2>
                                </div>
                            </div>
                            <div class="chart-box">
                                <div v-loading="!asyncComponent">
                                    <div class="data-range-picker">Last 6 months <i class="mdi mdi-chevron-down ml-10"></i></div>
                                    <component
                                        :is="asyncComponent"
                                        :type="'line'"
                                        :options="{
                                            width: '100%',
                                            height: 200,
                                            fill: ['rgba(8, 124, 210, 0.25)'],
                                            stroke: 'rgba(8, 124, 210, 0.75)',
                                            strokeWidth: 2
                                        }"
                                        :data="[1, 3, 2, 4, 4, 9, 3, 4, 6, 5, 4, 6, 9, 8, 11, 12, 13, 12, 12, 14].toString()"
                                    />
                                    <div class="flex justify-space-around labels" v-if="asyncComponent">
                                        <span>FEB</span>
                                        <span>MAR</span>
                                        <span>APR</span>
                                        <span>MAY</span>
                                        <span>JUN</span>
                                        <span>JUL</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :sm="24" :md="12" :lg="10" :xl="10">
                    <div class="bg-white chart-wallet-box">
                        <div id="chartWallet" style="height: 500px; width: 98%"></div>
                    </div>
                </el-col>
            </el-row>
        </div>

        <el-row class="mt-30" :gutter="30">
            <el-col :xs="24" :sm="12" :md="10" :lg="10" :xl="10" class="conversion-widget">
                <h2 class="conversion-title">Conversion History</h2>
                <el-scrollbar class="card-base card-outline p-10 mb-30" style="height: 660px">
                    <table class="conversion-table">
                        <thead>
                            <tr>
                                <th class="text-center">Type</th>
                                <th class="text-center">Date</th>
                                <th class="text-center">Amount</th>
                                <th class="text-center">Fee</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(i, index) in conversionHistory" :key="index">
                                <td class="text-center tokens">
                                    <span>{{ i.t_a }}</span>
                                    <i class="mdi mdi-swap-horizontal"></i>
                                    <span>{{ i.t_b }}</span>
                                </td>
                                <td class="text-center">{{ i.date }}/{{ year }}</td>
                                <td class="text-center fw-700">${{ i.amount }}</td>
                                <td class="text-center danger-text">-${{ i.fee }}</td>
                            </tr>
                        </tbody>
                    </table>
                </el-scrollbar>
            </el-col>
            <el-col :xs="24" :sm="12" :md="14" :lg="14" :xl="14" class="conversion-widget">
                <h2 class="conversion-title">Quick Conversion</h2>
                <el-scrollbar class="card-base card-outline ph-20 pt-5 pb-15 mb-30" style="height: 660px">
                    <el-tabs class="themed">
                        <el-tab-pane label="Limit">
                            <div>
                                <el-row :gutter="30">
                                    <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12">
                                        <div class="title flex justify-space-between mb-20">
                                            <div>Buy BTC</div>
                                            <div class="o-050">USD Balance: $ 8354.36</div>
                                        </div>
                                        <div class="form mb-20" style="overflow: hidden">
                                            <el-form label-width="70px">
                                                <el-form-item label="Price">
                                                    <el-input class="themed" placeholder="$ 6384,43"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Amount">
                                                    <el-input class="themed" placeholder="0.0373 BTC"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Total">
                                                    <el-input class="themed" placeholder="$ 747,36"></el-input>
                                                </el-form-item>
                                                <el-button class="themed" type="primary" plain style="float: right"> Buy BTC </el-button>
                                            </el-form>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12">
                                        <div class="title flex justify-space-between mb-20">
                                            <div>Sell BTC</div>
                                            <div class="o-050">BTC Balance: 1.038748</div>
                                        </div>
                                        <div class="form mb-20" style="overflow: hidden">
                                            <el-form label-width="70px">
                                                <el-form-item label="Price">
                                                    <el-input class="themed" placeholder="$ 9848,38"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Amount">
                                                    <el-input class="themed" placeholder="0.083837 BTC"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Total">
                                                    <el-input class="themed" placeholder="$ 83638,76"></el-input>
                                                </el-form-item>
                                                <el-button class="themed" type="primary" plain style="float: right"> Sell BTC </el-button>
                                            </el-form>
                                        </div>
                                    </el-col>
                                </el-row>
                            </div>
                        </el-tab-pane>
                        <el-tab-pane label="Market">
                            <div>
                                <el-row :gutter="30">
                                    <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12">
                                        <div class="title flex justify-space-between mb-20">
                                            <div>Buy BTC</div>
                                            <div class="o-050">USD Balance: $ 8354.36</div>
                                        </div>
                                        <div class="form mb-20" style="overflow: hidden">
                                            <el-form label-width="70px">
                                                <el-form-item label="Price">
                                                    <el-input class="themed" placeholder="$ 6384,43"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Amount">
                                                    <el-input class="themed" placeholder="0.0373 BTC"></el-input>
                                                </el-form-item>
                                                <el-button class="themed" type="primary" plain style="float: right"> Buy BTC </el-button>
                                            </el-form>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12">
                                        <div class="title flex justify-space-between mb-20">
                                            <div>Sell BTC</div>
                                            <div class="o-050">BTC Balance: 1.038748</div>
                                        </div>
                                        <div class="form mb-20" style="overflow: hidden">
                                            <el-form label-width="70px">
                                                <el-form-item label="Price">
                                                    <el-input class="themed" placeholder="$ 9848,38"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Amount">
                                                    <el-input class="themed" placeholder="0.083837 BTC"></el-input>
                                                </el-form-item>
                                                <el-button class="themed" type="primary" plain style="float: right"> Sell BTC </el-button>
                                            </el-form>
                                        </div>
                                    </el-col>
                                </el-row>
                            </div>
                        </el-tab-pane>
                        <el-tab-pane label="Stop Limit">
                            <div>
                                <el-row :gutter="30">
                                    <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12">
                                        <div class="title flex justify-space-between mb-20">
                                            <div>Buy BTC</div>
                                            <div class="o-050">USD Balance: $ 8354.36</div>
                                        </div>
                                        <div class="form mb-20" style="overflow: hidden">
                                            <el-form label-width="70px">
                                                <el-form-item label="Stop">
                                                    <el-input class="themed" placeholder="$ 6384,43"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Limit">
                                                    <el-input class="themed" placeholder="0.0373 BTC"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Amount">
                                                    <el-input class="themed" placeholder="$ 747,36"></el-input>
                                                </el-form-item>
                                                <el-button class="themed" type="primary" plain style="float: right"> Buy BTC </el-button>
                                            </el-form>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="24" :md="24" :lg="12" :xl="12">
                                        <div class="title flex justify-space-between mb-20">
                                            <div>Sell BTC</div>
                                            <div class="o-050">BTC Balance: 1.038748</div>
                                        </div>
                                        <div class="form mb-20" style="overflow: hidden">
                                            <el-form label-width="70px">
                                                <el-form-item label="Stop">
                                                    <el-input class="themed" placeholder="$ 9848,38"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Limit">
                                                    <el-input class="themed" placeholder="0.083837 BTC"></el-input>
                                                </el-form-item>
                                                <el-form-item label="Amount">
                                                    <el-input class="themed" placeholder="$ 83638,76"></el-input>
                                                </el-form-item>
                                                <el-button class="themed" type="primary" plain style="float: right"> Sell BTC </el-button>
                                            </el-form>
                                        </div>
                                    </el-col>
                                </el-row>
                            </div>
                        </el-tab-pane>
                    </el-tabs>
                </el-scrollbar>
            </el-col>
        </el-row>
    </el-scrollbar>
</template>

<script>
import MarqueeInfinite from "marquee-infinite"
import * as echarts from "echarts"
import "cryptocoins-icons/webfont/cryptocoins.css"
import "cryptocoins-icons/webfont/cryptocoins-colors.css"
import ResizeObserver from "../../components/vue-resize/ResizeObserver.vue"
import _throttle from "lodash/throttle"
import { defineComponent } from "vue"
import Peity from "../../components/vue-peity/Peity.vue"

export default defineComponent({
    name: "CryptoDashboard",
    data() {
        return {
            asyncComponent: "peity",
            resized: false,
            marquee: null,
            chartWallet: null,
            chartPrice: null,
            chartCandle: null,
            cryptocoins: [
                {
                    ico: "BTC",
                    name: "Bitcoin",
                    price: "$6.307,52"
                },
                {
                    ico: "ETH",
                    name: "Ethereum",
                    price: "$200,14"
                },
                {
                    ico: "XRP",
                    name: "XRP",
                    price: "$0,273904"
                },
                {
                    ico: "XLM",
                    name: "Stellar",
                    price: "$0,196676"
                },
                {
                    ico: "LTC",
                    name: "Litecoin",
                    price: "$52,18"
                },
                {
                    ico: "USDT",
                    name: "Tether",
                    price: "$1,00"
                },
                {
                    ico: "XMR",
                    name: "Monero",
                    price: "$109,88"
                },
                {
                    ico: "DASH",
                    name: "Dash",
                    price: "$183,62"
                },
                {
                    ico: "NEO",
                    name: "NEO",
                    price: "$16,71"
                },
                {
                    ico: "XTZ",
                    name: "Tezos",
                    price: "$1,46"
                },
                {
                    ico: "XEM",
                    name: "NEM",
                    price: "$0,085573"
                },
                {
                    ico: "ZEC",
                    name: "Zcash",
                    price: "$111,73"
                },
                {
                    ico: "OMG",
                    name: "OmiseGO",
                    price: "$3,12"
                },
                {
                    ico: "LSK",
                    name: "Lisk",
                    price: "$3,40"
                },
                {
                    ico: "BCN",
                    name: "Bytecoin",
                    price: "$0,001815"
                },
                {
                    ico: "DCR",
                    name: "Decred",
                    price: "$35,83"
                },
                {
                    ico: "QTUM",
                    name: "Qtum",
                    price: "$3,22"
                },
                {
                    ico: "REP",
                    name: "Augur",
                    price: "$12,40"
                },
                {
                    ico: "STRAT",
                    name: "Stratis",
                    price: "$1,29"
                },
                {
                    ico: "MCO",
                    name: "MCO",
                    price: "$4,14"
                }
            ],
            selectWalletOpen: false,
            year: new Date().getFullYear(),
            conversionHistory: [
                { t_a: "BTC", t_b: "USD", date: "03/10", amount: "25,38", fee: "1,23" },
                { t_a: "RPX", t_b: "ETH", date: "01/10", amount: "15,21", fee: "1,13" },
                { t_a: "LTC", t_b: "BTC", date: "27/09", amount: "17,43", fee: "2,14" },
                { t_a: "PRX", t_b: "LTC", date: "25/09", amount: "23,18", fee: "3,17" },
                { t_a: "ETH", t_b: "USD", date: "22/09", amount: "35,42", fee: "3,12" },
                { t_a: "BTC", t_b: "ETH", date: "20/09", amount: "72,62", fee: "4,15" },
                { t_a: "RPX", t_b: "USD", date: "19/09", amount: "25,38", fee: "1,23" },
                { t_a: "BTC", t_b: "USD", date: "17/09", amount: "25,38", fee: "1,23" },
                { t_a: "ETH", t_b: "BTC", date: "16/09", amount: "52,11", fee: "4,72" },
                { t_a: "BTC", t_b: "USD", date: "14/09", amount: "25,38", fee: "1,23" },
                { t_a: "RPX", t_b: "ETH", date: "13/09", amount: "15,21", fee: "1,13" },
                { t_a: "LTC", t_b: "BTC", date: "10/09", amount: "17,43", fee: "2,14" },
                { t_a: "PRX", t_b: "LTC", date: "09/09", amount: "23,18", fee: "3,17" },
                { t_a: "ETH", t_b: "USD", date: "08/09", amount: "35,42", fee: "3,12" },
                { t_a: "BTC", t_b: "ETH", date: "07/09", amount: "72,62", fee: "4,15" },
                { t_a: "RPX", t_b: "USD", date: "06/09", amount: "25,38", fee: "1,23" }
                /*{ t_a: "BTC", t_b: "USD", date: "05/09", amount: "25,38", fee: "1,23" },
                { t_a: "ETH", t_b: "BTC", date: "04/09", amount: "52,11", fee: "4,72" },
                { t_a: "BTC", t_b: "USD", date: "01/09", amount: "25,38", fee: "1,23" },
                { t_a: "RPX", t_b: "ETH", date: "29/08", amount: "15,21", fee: "1,13" },
                { t_a: "LTC", t_b: "BTC", date: "28/08", amount: "17,43", fee: "2,14" },
                { t_a: "PRX", t_b: "LTC", date: "26/08", amount: "23,18", fee: "3,17" },
                { t_a: "ETH", t_b: "USD", date: "24/08", amount: "35,42", fee: "3,12" },
                { t_a: "BTC", t_b: "ETH", date: "21/08", amount: "72,62", fee: "4,15" },
                { t_a: "RPX", t_b: "USD", date: "20/08", amount: "25,38", fee: "1,23" },
                { t_a: "BTC", t_b: "USD", date: "18/08", amount: "25,38", fee: "1,23" },
                { t_a: "ETH", t_b: "BTC", date: "16/08", amount: "52,11", fee: "4,72" },
                { t_a: "BTC", t_b: "USD", date: "15/08", amount: "25,38", fee: "1,23" },
                { t_a: "RPX", t_b: "ETH", date: "13/08", amount: "15,21", fee: "1,13" },
                { t_a: "LTC", t_b: "BTC", date: "11/08", amount: "17,43", fee: "2,14" },
                { t_a: "PRX", t_b: "LTC", date: "09/08", amount: "23,18", fee: "3,17" },
                { t_a: "ETH", t_b: "USD", date: "07/08", amount: "35,42", fee: "3,12" },
                { t_a: "BTC", t_b: "ETH", date: "05/08", amount: "72,62", fee: "4,15" },
                { t_a: "RPX", t_b: "USD", date: "04/08", amount: "25,38", fee: "1,23" },
                { t_a: "BTC", t_b: "USD", date: "03/08", amount: "25,38", fee: "1,23" },
                { t_a: "ETH", t_b: "BTC", date: "01/08", amount: "52,11", fee: "4,72" }*/
            ]
        }
    },
    computed: {},
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
            }
            this.resized = true
        }, 700),
        removePeity() {
            const peityEl = document.querySelectorAll(".peity") //.forEach((el)=>{el.remove()})
            //ie fix
            for (let i = 0; i < peityEl.length; i++) {
                peityEl[i].parentNode.removeChild(peityEl[i])
            }
        },
        initMarquee() {
            this.marquee = new MarqueeInfinite("#crypto-banner", {
                maxItems: 80,
                duration: 50000,
                classNames: {
                    container: "marqueeInfinite",
                    slider: "marqueeInfiniteSlider",
                    cell: "marqueeInfiniteCell"
                }
            })
        },
        initChartWallet() {
            const scale = 1
            const chartWalletData = [
                {
                    value: 23,
                    name: "Bitcoin",
                    itemStyle: {
                        borderWidth: 5,
                        //shadowBlur: 20,
                        borderColor: "#3f84f6"
                        //shadowColor: '#00cfff'
                    }
                },
                {
                    value: 62,
                    name: "Dash",
                    itemStyle: {
                        borderWidth: 5,
                        //shadowBlur: 20,
                        borderColor: "#2673f5"
                        //shadowColor: '#00a4ca'
                    }
                },
                {
                    value: 12,
                    name: "Stellar",
                    itemStyle: {
                        borderWidth: 5,
                        //shadowBlur: 20,
                        borderColor: "#4889f6"
                        //shadowColor: '#007590'
                    }
                },
                {
                    value: 31,
                    name: "Ethereum",
                    itemStyle: {
                        borderWidth: 5,
                        //shadowBlur: 20,
                        borderColor: "#74a6f8"
                        //shadowColor: '#005390'
                    }
                },
                {
                    value: 59,
                    name: "Litecoin",
                    itemStyle: {
                        borderWidth: 5,
                        //shadowBlur: 20,
                        borderColor: "#a4c5fb"
                        //shadowColor: '#087cd2'
                    }
                }
            ]

            const rich = {
                value: {
                    color: "#0394ff",
                    fontSize: 20 * scale,
                    fontFamily: "Nunito Sans",
                    padding: [2, 0],
                    align: "center"
                },
                total: {
                    color: "#0394ff",
                    fontSize: 40 * scale,
                    fontFamily: "Nunito Sans",
                    align: "center"
                },
                title: {
                    color: "#000",
                    align: "center",
                    fontSize: 14 * scale,
                    fontFamily: "Nunito Sans",
                    borderWidth: 1,
                    borderColor: "#0b5263",
                    padding: [5, 5]
                },
                percent: {
                    color: "#888",
                    fontSize: 12 * scale,
                    fontFamily: "Nunito Sans",
                    align: "center",
                    padding: [5, 0]
                }
                /*hr: {
					borderColor: '#0b5263',
					width: '100%',
					borderWidth: 1,
					height: 0,
					top: '10%'
				}*/
            }

            this.chartWallet = echarts.init(document.getElementById("chartWallet"))
            this.chartWallet.setOption({
                title: {
                    text: "coins",
                    left: "center",
                    top: "47%",
                    padding: [24, 0],
                    textStyle: {
                        color: "#000",
                        fontSize: 18 * scale,
                        fontFamily: "Nunito Sans",
                        align: "center"
                    }
                },
                legend: {
                    selectedMode: false,
                    formatter: function (name) {
                        var total = 0
                        var averagePercent
                        chartWalletData.forEach(function (value, index, array) {
                            total += value.value
                        })
                        return "{total|" + total + "}"
                    },
                    data: [chartWalletData[0].name],
                    // data: [''],
                    // itemGap: 50,
                    left: "center",
                    top: "43%",
                    icon: "none",
                    align: "center",
                    textStyle: {
                        color: "#fff",
                        fontSize: 16 * scale,
                        fontFamily: "Nunito Sans",
                        rich: rich
                    }
                },
                series: [
                    {
                        name: "coins",
                        type: "pie",
                        radius: ["37%", "45%"],
                        color: ["#3f84f6", "#2673f5", "#4889f6", "#74a6f8", "#a4c5fb"],
                        label: {
                            formatter: function (params, ticket, callback) {
                                var total = 0
                                var percent = 0
                                chartWalletData.forEach(function (value, index, array) {
                                    total += value.value
                                })
                                percent = ((params.value / total) * 100).toFixed(1)
                                return "{value|" + params.value + "}\n{title|" + params.name + "}\n{percent|" + percent + "%}"
                                //return '{white|' + params.name + '}\n{hr|}\n{yellow|' + params.value + '}\n{blue|' + percent + '%}';
                            },
                            rich: rich
                        },
                        labelLine: {
                            length: 35 * scale,
                            length2: 0,
                            lineStyle: {
                                color: "#0b5263"
                            }
                        },
                        data: chartWalletData
                    }
                ]
            })
        },
        initChartPrice() {
            const chartOptions = {
                title: {
                    text: "BTC/USD",
                    top: 0,
                    right: 0,
                    textStyle: {
                        fontSize: 14
                    }
                },
                legend: {
                    show: !1
                },
                grid: {
                    show: false,
                    left: -25,
                    right: 10,
                    bottom: 40,
                    top: 10,
                    containLabel: true
                },
                tooltip: {
                    trigger: "axis",
                    formatter: function (e) {
                        var t = e[0].seriesName + " - " + e[0].name
                        return (
                            (t += "<br/>  Opening : " + e[0].value[0]),
                            (t += "<br/>  Closing : $ " + e[0].value[1]),
                            (t += "<br/>  Highest : $ " + e[0].value[3]),
                            (t += "<br/>  Lowest : $ " + e[0].value[2])
                        )
                    },
                    axisPointer: {
                        type: "line",
                        lineStyle: {
                            color: "#fff",
                            width: 2,
                            type: "solid"
                        }
                    }
                },
                legend: {
                    show: !1,
                    data: ["BTC"]
                },
                dataZoom: {
                    show: !0,
                    realtime: !0,
                    start: 0,
                    end: 50
                },
                color: ["#24CB8C", "#1EC481", "#18BE77"],
                calculable: !0,
                xAxis: [
                    {
                        type: "category",
                        boundaryGap: !0,
                        axisLine: {
                            lineStyle: {
                                color: "#fff"
                            }
                        },
                        axisTick: {
                            onGap: !1
                        },
                        splitLine: {
                            show: !1
                        },
                        data: [
                            "1/24",
                            "1/25",
                            "1/28",
                            "1/29",
                            "1/30",
                            "1/31",
                            "2/1",
                            "2/4",
                            "2/5",
                            "2/6",
                            "2/7",
                            "2/8",
                            "2/18",
                            "2/19",
                            "2/20",
                            "2/21",
                            "2/22",
                            "2/25",
                            "2/26",
                            "2/27",
                            "2/28",
                            "3/1",
                            "3/4",
                            "3/5",
                            "3/6",
                            "3/7",
                            "3/8",
                            "3/11",
                            "3/12",
                            "3/13",
                            "3/14",
                            "3/15",
                            "3/18",
                            "3/19",
                            "3/20",
                            "3/21",
                            "3/22",
                            "3/25",
                            "3/26",
                            "3/27",
                            "3/28",
                            "3/29",
                            "4/1",
                            "4/2",
                            "4/3",
                            "4/8",
                            "4/9",
                            "4/10",
                            "4/11",
                            "4/12",
                            "4/15",
                            "4/16",
                            "4/17",
                            "4/18",
                            "4/19",
                            "4/22",
                            "4/23",
                            "4/24",
                            "4/25",
                            "4/26",
                            "5/2",
                            "5/3",
                            "5/6",
                            "5/7",
                            "5/8",
                            "5/9",
                            "5/10",
                            "5/13",
                            "5/14",
                            "5/15",
                            "5/16",
                            "5/17",
                            "5/20",
                            "5/21",
                            "5/22",
                            "5/23",
                            "5/24",
                            "5/27",
                            "5/28",
                            "5/29",
                            "5/30",
                            "5/31",
                            "6/3",
                            "6/4",
                            "6/5",
                            "6/6",
                            "6/7",
                            "6/13"
                        ]
                    }
                ],
                yAxis: [
                    {
                        show: false,
                        type: "value",
                        scale: !0,
                        boundaryGap: [0.01, 0.01],
                        axisLine: {
                            lineStyle: {
                                color: "#fff"
                            }
                        },
                        splitLine: {
                            lineStyle: {
                                color: "#e3e3e3"
                            }
                        }
                    }
                ],
                series: [
                    {
                        name: "BTC",
                        type: "k",
                        barMaxWidth: 20,
                        itemStyle: {
                            color: "#94E8CA",
                            color0: "#FFA4B0",
                            lineStyle: {
                                width: 2,
                                color: "#28D094",
                                color0: "#FF4961"
                            }
                        },
                        data: [
                            {
                                value: [2320.26, 2302.6, 2287.3, 2362.94],
                                itemStyle: {
                                    color0: "#FFA4B0",
                                    lineStyle: {
                                        width: 3,
                                        color0: "#FF4961"
                                    }
                                }
                            },
                            [2300, 2291.3, 2288.26, 2308.38],
                            [2295.35, 2346.5, 2295.35, 2346.92],
                            [2347.22, 2358.98, 2337.35, 2363.8],
                            [2360.75, 2382.48, 2347.89, 2383.76],
                            [2383.43, 2385.42, 2371.23, 2391.82],
                            [2377.41, 2419.02, 2369.57, 2421.15],
                            [2425.92, 2428.15, 2417.58, 2440.38],
                            [2411, 2433.13, 2403.3, 2437.42],
                            [2432.68, 2434.48, 2427.7, 2441.73],
                            [2430.69, 2418.53, 2394.22, 2433.89],
                            [2416.62, 2432.4, 2414.4, 2443.03],
                            [2441.91, 2421.56, 2415.43, 2444.8],
                            [2420.26, 2382.91, 2373.53, 2427.07],
                            [2383.49, 2397.18, 2370.61, 2397.94],
                            [2378.82, 2325.95, 2309.17, 2378.82],
                            [2322.94, 2314.16, 2308.76, 2330.88],
                            [2320.62, 2325.82, 2315.01, 2338.78],
                            [2313.74, 2293.34, 2289.89, 2340.71],
                            [2297.77, 2313.22, 2292.03, 2324.63],
                            [2322.32, 2365.59, 2308.92, 2366.16],
                            [2364.54, 2359.51, 2330.86, 2369.65],
                            [2332.08, 2273.4, 2259.25, 2333.54],
                            [2274.81, 2326.31, 2270.1, 2328.14],
                            [2333.61, 2347.18, 2321.6, 2351.44],
                            [2340.44, 2324.29, 2304.27, 2352.02],
                            [2326.42, 2318.61, 2314.59, 2333.67],
                            [2314.68, 2310.59, 2296.58, 2320.96],
                            [2309.16, 2286.6, 2264.83, 2333.29],
                            [2282.17, 2263.97, 2253.25, 2286.33],
                            [2255.77, 2270.28, 2253.31, 2276.22],
                            [2269.31, 2278.4, 2250, 2312.08],
                            [2267.29, 2240.02, 2239.21, 2276.05],
                            [2244.26, 2257.43, 2232.02, 2261.31],
                            [2257.74, 2317.37, 2257.42, 2317.86],
                            [2318.21, 2324.24, 2311.6, 2330.81],
                            [2321.4, 2328.28, 2314.97, 2332],
                            [2334.74, 2326.72, 2319.91, 2344.89],
                            [2318.58, 2297.67, 2281.12, 2319.99],
                            [2299.38, 2301.26, 2289, 2323.48],
                            [2273.55, 2236.3, 2232.91, 2273.55],
                            [2238.49, 2236.62, 2228.81, 2246.87],
                            [2229.46, 2234.4, 2227.31, 2243.95],
                            [2234.9, 2227.74, 2220.44, 2253.42],
                            [2232.69, 2225.29, 2217.25, 2241.34],
                            [2196.24, 2211.59, 2180.67, 2212.59],
                            [2215.47, 2225.77, 2215.47, 2234.73],
                            [2224.93, 2226.13, 2212.56, 2233.04],
                            [2236.98, 2219.55, 2217.26, 2242.48],
                            [2218.09, 2206.78, 2204.44, 2226.26],
                            [2199.91, 2181.94, 2177.39, 2204.99],
                            [2169.63, 2194.85, 2165.78, 2196.43],
                            [2195.03, 2193.8, 2178.47, 2197.51],
                            [2181.82, 2197.6, 2175.44, 2206.03],
                            [2201.12, 2244.64, 2200.58, 2250.11],
                            [2236.4, 2242.17, 2232.26, 2245.12],
                            [2242.62, 2184.54, 2182.81, 2242.62],
                            [2187.35, 2218.32, 2184.11, 2226.12],
                            [2213.19, 2199.31, 2191.85, 2224.63],
                            [2203.89, 2177.91, 2173.86, 2210.58],
                            [2170.78, 2174.12, 2161.14, 2179.65],
                            [2179.05, 2205.5, 2179.05, 2222.81],
                            [2212.5, 2231.17, 2212.5, 2236.07],
                            [2227.86, 2235.57, 2219.44, 2240.26],
                            [2242.39, 2246.3, 2235.42, 2255.21],
                            [2246.96, 2232.97, 2221.38, 2247.86],
                            [2228.82, 2246.83, 2225.81, 2247.67],
                            [2247.68, 2241.92, 2231.36, 2250.85],
                            [2238.9, 2217.01, 2205.87, 2239.93],
                            [2217.09, 2224.8, 2213.58, 2225.19],
                            [2221.34, 2251.81, 2210.77, 2252.87],
                            [2249.81, 2282.87, 2248.41, 2288.09],
                            [2286.33, 2299.99, 2281.9, 2309.39],
                            [2297.11, 2305.11, 2290.12, 2305.3],
                            [2303.75, 2302.4, 2292.43, 2314.18],
                            [2293.81, 2275.67, 2274.1, 2304.95],
                            [2281.45, 2288.53, 2270.25, 2292.59],
                            [2286.66, 2293.08, 2283.94, 2301.7],
                            [2293.4, 2321.32, 2281.47, 2322.1],
                            [2323.54, 2324.02, 2321.17, 2334.33],
                            [2316.25, 2317.75, 2310.49, 2325.72],
                            [2320.74, 2300.59, 2299.37, 2325.53],
                            [2300.21, 2299.25, 2294.11, 2313.43],
                            [2297.1, 2272.42, 2264.76, 2297.1],
                            [2270.71, 2270.93, 2260.87, 2276.86],
                            [2264.43, 2242.11, 2240.07, 2266.69],
                            [2242.26, 2210.9, 2205.07, 2250.63],
                            [2190.1, 2148.35, 2126.22, 2190.1]
                        ]
                    }
                ]
            }

            this.chartPrice = echarts.init(document.getElementById("priceChart"))
            this.chartPrice.setOption(chartOptions)
        },
        initChartCandle() {
            const chartOptions = {
                title: {
                    text: "",
                    top: 0,
                    right: 0,
                    textStyle: {
                        fontSize: 14
                    }
                },
                legend: {
                    show: !1
                },
                grid: {
                    show: false,
                    left: -25,
                    right: 10,
                    bottom: 40,
                    top: 10,
                    containLabel: true
                },
                tooltip: {
                    trigger: "axis",
                    formatter: function (e) {
                        var t = e[0].seriesName + " - " + e[0].name
                        return (
                            (t += "<br/>  Opening : " + e[0].value[0]),
                            (t += "<br/>  Closing : $ " + e[0].value[1]),
                            (t += "<br/>  Highest : $ " + e[0].value[3]),
                            (t += "<br/>  Lowest : $ " + e[0].value[2])
                        )
                    },
                    axisPointer: {
                        type: "line",
                        lineStyle: {
                            color: "#fff",
                            width: 2,
                            type: "solid"
                        }
                    }
                },
                legend: {
                    show: !1,
                    data: ["BTC"]
                },
                dataZoom: {
                    show: !0,
                    realtime: !0,
                    start: 0,
                    end: 50
                },
                color: ["#24CB8C", "#1EC481", "#18BE77"],
                calculable: !0,
                xAxis: [
                    {
                        type: "category",
                        boundaryGap: !0,
                        axisLine: {
                            lineStyle: {
                                color: "#fff"
                            }
                        },
                        axisTick: {
                            onGap: !1
                        },
                        splitLine: {
                            show: !1
                        },
                        data: [
                            "1/24",
                            "1/25",
                            "1/28",
                            "1/29",
                            "1/30",
                            "1/31",
                            "2/1",
                            "2/4",
                            "2/5",
                            "2/6",
                            "2/7",
                            "2/8",
                            "2/18",
                            "2/19",
                            "2/20",
                            "2/21",
                            "2/22",
                            "2/25",
                            "2/26",
                            "2/27",
                            "2/28",
                            "3/1",
                            "3/4",
                            "3/5",
                            "3/6",
                            "3/7",
                            "3/8",
                            "3/11",
                            "3/12",
                            "3/13",
                            "3/14",
                            "3/15",
                            "3/18",
                            "3/19",
                            "3/20",
                            "3/21",
                            "3/22",
                            "3/25",
                            "3/26",
                            "3/27",
                            "3/28",
                            "3/29",
                            "4/1",
                            "4/2",
                            "4/3",
                            "4/8",
                            "4/9",
                            "4/10",
                            "4/11",
                            "4/12",
                            "4/15",
                            "4/16",
                            "4/17",
                            "4/18",
                            "4/19",
                            "4/22",
                            "4/23",
                            "4/24",
                            "4/25",
                            "4/26",
                            "5/2",
                            "5/3",
                            "5/6",
                            "5/7",
                            "5/8",
                            "5/9",
                            "5/10",
                            "5/13",
                            "5/14",
                            "5/15",
                            "5/16",
                            "5/17",
                            "5/20",
                            "5/21",
                            "5/22",
                            "5/23",
                            "5/24",
                            "5/27",
                            "5/28",
                            "5/29",
                            "5/30",
                            "5/31",
                            "6/3",
                            "6/4",
                            "6/5",
                            "6/6",
                            "6/7",
                            "6/13"
                        ]
                    }
                ],
                yAxis: [
                    {
                        show: false,
                        type: "value",
                        scale: !0,
                        boundaryGap: [0.01, 0.01],
                        axisLine: {
                            lineStyle: {
                                color: "#fff"
                            }
                        },
                        splitLine: {
                            lineStyle: {
                                color: "#e3e3e3"
                            }
                        }
                    }
                ],
                series: [
                    {
                        name: "BTC",
                        type: "k",
                        barMaxWidth: 20,
                        itemStyle: {
                            color: "#94E8CA",
                            color0: "#FFA4B0",
                            lineStyle: {
                                width: 2,
                                color: "#28D094",
                                color0: "#FF4961"
                            }
                        },
                        data: [
                            {
                                value: [2320.26, 2302.6, 2287.3, 2362.94],
                                itemStyle: {
                                    color0: "#FFA4B0",
                                    lineStyle: {
                                        width: 3,
                                        color0: "#FF4961"
                                    }
                                }
                            },
                            [2300, 2291.3, 2288.26, 2308.38],
                            [2295.35, 2346.5, 2295.35, 2346.92],
                            [2347.22, 2358.98, 2337.35, 2363.8],
                            [2360.75, 2382.48, 2347.89, 2383.76],
                            [2383.43, 2385.42, 2371.23, 2391.82],
                            [2377.41, 2419.02, 2369.57, 2421.15],
                            [2425.92, 2428.15, 2417.58, 2440.38],
                            [2411, 2433.13, 2403.3, 2437.42],
                            [2432.68, 2434.48, 2427.7, 2441.73],
                            [2430.69, 2418.53, 2394.22, 2433.89],
                            [2416.62, 2432.4, 2414.4, 2443.03],
                            [2441.91, 2421.56, 2415.43, 2444.8],
                            [2420.26, 2382.91, 2373.53, 2427.07],
                            [2383.49, 2397.18, 2370.61, 2397.94],
                            [2378.82, 2325.95, 2309.17, 2378.82],
                            [2322.94, 2314.16, 2308.76, 2330.88],
                            [2320.62, 2325.82, 2315.01, 2338.78],
                            [2313.74, 2293.34, 2289.89, 2340.71],
                            [2297.77, 2313.22, 2292.03, 2324.63],
                            [2322.32, 2365.59, 2308.92, 2366.16],
                            [2364.54, 2359.51, 2330.86, 2369.65],
                            [2332.08, 2273.4, 2259.25, 2333.54],
                            [2274.81, 2326.31, 2270.1, 2328.14],
                            [2333.61, 2347.18, 2321.6, 2351.44],
                            [2340.44, 2324.29, 2304.27, 2352.02],
                            [2326.42, 2318.61, 2314.59, 2333.67],
                            [2314.68, 2310.59, 2296.58, 2320.96],
                            [2309.16, 2286.6, 2264.83, 2333.29],
                            [2282.17, 2263.97, 2253.25, 2286.33],
                            [2255.77, 2270.28, 2253.31, 2276.22],
                            [2269.31, 2278.4, 2250, 2312.08],
                            [2267.29, 2240.02, 2239.21, 2276.05],
                            [2244.26, 2257.43, 2232.02, 2261.31],
                            [2257.74, 2317.37, 2257.42, 2317.86],
                            [2318.21, 2324.24, 2311.6, 2330.81],
                            [2321.4, 2328.28, 2314.97, 2332],
                            [2334.74, 2326.72, 2319.91, 2344.89],
                            [2318.58, 2297.67, 2281.12, 2319.99],
                            [2299.38, 2301.26, 2289, 2323.48],
                            [2273.55, 2236.3, 2232.91, 2273.55],
                            [2238.49, 2236.62, 2228.81, 2246.87],
                            [2229.46, 2234.4, 2227.31, 2243.95],
                            [2234.9, 2227.74, 2220.44, 2253.42],
                            [2232.69, 2225.29, 2217.25, 2241.34],
                            [2196.24, 2211.59, 2180.67, 2212.59],
                            [2215.47, 2225.77, 2215.47, 2234.73],
                            [2224.93, 2226.13, 2212.56, 2233.04],
                            [2236.98, 2219.55, 2217.26, 2242.48],
                            [2218.09, 2206.78, 2204.44, 2226.26],
                            [2199.91, 2181.94, 2177.39, 2204.99],
                            [2169.63, 2194.85, 2165.78, 2196.43],
                            [2195.03, 2193.8, 2178.47, 2197.51],
                            [2181.82, 2197.6, 2175.44, 2206.03],
                            [2201.12, 2244.64, 2200.58, 2250.11],
                            [2236.4, 2242.17, 2232.26, 2245.12],
                            [2242.62, 2184.54, 2182.81, 2242.62],
                            [2187.35, 2218.32, 2184.11, 2226.12],
                            [2213.19, 2199.31, 2191.85, 2224.63],
                            [2203.89, 2177.91, 2173.86, 2210.58],
                            [2170.78, 2174.12, 2161.14, 2179.65],
                            [2179.05, 2205.5, 2179.05, 2222.81],
                            [2212.5, 2231.17, 2212.5, 2236.07],
                            [2227.86, 2235.57, 2219.44, 2240.26],
                            [2242.39, 2246.3, 2235.42, 2255.21],
                            [2246.96, 2232.97, 2221.38, 2247.86],
                            [2228.82, 2246.83, 2225.81, 2247.67],
                            [2247.68, 2241.92, 2231.36, 2250.85],
                            [2238.9, 2217.01, 2205.87, 2239.93],
                            [2217.09, 2224.8, 2213.58, 2225.19],
                            [2221.34, 2251.81, 2210.77, 2252.87],
                            [2249.81, 2282.87, 2248.41, 2288.09],
                            [2286.33, 2299.99, 2281.9, 2309.39],
                            [2297.11, 2305.11, 2290.12, 2305.3],
                            [2303.75, 2302.4, 2292.43, 2314.18],
                            [2293.81, 2275.67, 2274.1, 2304.95],
                            [2281.45, 2288.53, 2270.25, 2292.59],
                            [2286.66, 2293.08, 2283.94, 2301.7],
                            [2293.4, 2321.32, 2281.47, 2322.1],
                            [2323.54, 2324.02, 2321.17, 2334.33],
                            [2316.25, 2317.75, 2310.49, 2325.72],
                            [2320.74, 2300.59, 2299.37, 2325.53],
                            [2300.21, 2299.25, 2294.11, 2313.43],
                            [2297.1, 2272.42, 2264.76, 2297.1],
                            [2270.71, 2270.93, 2260.87, 2276.86],
                            [2264.43, 2242.11, 2240.07, 2266.69],
                            [2242.26, 2210.9, 2205.07, 2250.63],
                            [2190.1, 2148.35, 2126.22, 2190.1]
                        ]
                    }
                ]
            }

            this.chartCandle = echarts.init(document.getElementById("candleChart"))
            this.chartCandle.setOption(chartOptions)
        }
    },
    mounted() {
        setTimeout(() => {
            this.initMarquee()
        }, 100)

        setTimeout(() => {
            this.initChartWallet()
        }, 500)

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
    },
    components: { ResizeObserver, Peity }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

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
@import "../../assets/scss/_variables";

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
