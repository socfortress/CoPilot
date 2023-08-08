<template>
    <div class="page-ecommerce-products flex">
        <div :class="{ sidebar: true, open: sidebarOpen }">
            <el-scrollbar class="scroller">
                <div class="widget close-filter-box">
                    <button @click="sidebarOpen = false">close filter</button>
                </div>
                <div class="widget">
                    <div class="title">Category</div>
                    <div class="content">
                        <el-tree :data="treeData" :props="treeProps" node-key="id" :default-expanded-keys="[1]"></el-tree>
                    </div>
                </div>
                <div class="widget">
                    <div class="title">Price</div>
                    <div class="content">
                        <el-slider v-model="range" range :max="100" class="themed"></el-slider>
                        <div class="flex justify-space-between o-060">
                            <span>$ {{ range[0] }}</span>
                            <span>$ {{ range[1] }}</span>
                        </div>
                    </div>
                </div>
                <div class="widget select-color">
                    <div class="title">Colors</div>
                    <div class="content">
                        <ul>
                            <li>
                                <div class="color-box" style="background: #343a40"></div>
                                Black
                            </li>
                            <li>
                                <div class="color-box" style="background: #788db4"></div>
                                Grey
                            </li>
                            <li>
                                <div class="color-box" style="background: #736cc7"></div>
                                Purple
                            </li>
                            <li>
                                <div class="color-box" style="background: #f64a91"></div>
                                Pink
                            </li>
                            <li>
                                <div class="color-box" style="background: #ff5c75"></div>
                                Red
                            </li>
                            <li>
                                <div class="color-box" style="background: #399af2"></div>
                                Blue
                            </li>
                            <li>
                                <div class="color-box" style="background: #ffce67"></div>
                                Yellow
                            </li>
                            <li>
                                <div class="color-box" style="background: #2fbfa0"></div>
                                Green
                            </li>
                        </ul>
                    </div>
                </div>
                <div class="widget close-filter-box">
                    <button @click="sidebarOpen = false">close filter</button>
                </div>
            </el-scrollbar>
        </div>

        <div class="list-container box grow flex column">
            <div class="toggle-filter-box">
                <button @click="sidebarOpen = !sidebarOpen">
                    <span v-if="!sidebarOpen">open filter</span>
                    <span v-if="sidebarOpen">close filter</span>
                </button>
            </div>

            <div class="list scrollable only-y box grow">
                <div v-for="i in gridData" :key="i.id" class="item" @click="gotoDetail">
                    <div class="wrapper card-shadow--medium">
                        <button class="love-btn"><i class="mdi mdi-heart-outline"></i></button>
                        <div class="image p-20">
                            <div class="bg" :style="'background-image: url(' + i.photo + ')'"></div>
                        </div>
                        <div class="detail p-20">
                            <div class="rate">
                                <el-rate v-model="i.rate" disabled></el-rate>
                            </div>
                            <div class="name">
                                {{ i.product }}
                            </div>
                            <div class="desc">Lorem ipsum sit dolor amet</div>
                            <div class="price">$ {{ i.price }}</div>
                            <div class="buttons flex justify-space-between">
                                <button class="box grow">add to cart <i class="mdi mdi-cart-outline ml-5"></i></button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import _ from "lodash"
import { defineComponent } from "vue"

export default defineComponent({
    name: "EcommerceProducts",
    data() {
        return {
            gridData: [],
            sidebarOpen: false,
            range: [25, 75],
            treeData: [
                {
                    id: 1,
                    label: "Chairs",
                    children: [
                        {
                            label: "Dining chairs"
                        },
                        {
                            label: "Foldable chairs"
                        },
                        {
                            label: "Café chairs"
                        }
                    ]
                },
                {
                    label: "Café & bar chairs",
                    children: [
                        {
                            label: "Bar Stools"
                        },
                        {
                            label: "Café chairs"
                        }
                    ]
                },
                {
                    label: "Dining sets",
                    children: []
                },
                {
                    label: "Garden chairs",
                    children: [
                        {
                            label: "Garden chairs"
                        },
                        {
                            label: "Garden benches"
                        },
                        {
                            label: "Sun loungers & hammocks"
                        }
                    ]
                },
                {
                    label: "Stools & benches",
                    children: []
                },
                {
                    label: "Step stools",
                    children: []
                },
                {
                    label: "Junior chairs",
                    children: []
                },
                {
                    label: "High chairs",
                    children: []
                },
                {
                    label: "Armchairs",
                    children: [
                        {
                            label: "Fabric armchairs"
                        },
                        {
                            label: "Leather armchairs"
                        },
                        {
                            label: "Leather & coated fabric armchairs"
                        },
                        {
                            label: "Coated fabric armchairs"
                        },
                        {
                            label: "Rattan armchairs"
                        }
                    ]
                },
                {
                    label: "Office chairs",
                    children: [
                        {
                            label: "Swivel chairs"
                        },
                        {
                            label: "Visitor's chairs"
                        }
                    ]
                }
            ],
            treeProps: {
                children: "children",
                label: "label"
            }
        }
    },
    computed: {},
    methods: {
        initGridData() {
            _.times(50, number => {
                let price = chance.floating({ min: 1, max: 100, fixed: 2 })

                this.gridData.push({
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    product: chance.sentence({ words: 2 }),
                    price: _.replace(price.toFixed(2).toString(), ".", ","),
                    rate: chance.integer({ min: 3, max: 5 }),
                    id: number
                })
            })
        },
        gotoDetail() {
            this.$router.push({ name: "ecommerce-product-detail" })
        }
    },
    created() {
        this.initGridData()
    },
    mounted() {}
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-ecommerce-products {
    .sidebar {
        width: 300px;
        margin-right: 20px;
        margin-right: 10px;
        margin-left: -10px;

        .scroller {
            padding: 10px;
            padding-top: 0px;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
        }

        .widget {
            background: white;
            border-radius: 4px;
            margin-bottom: 20px;
            box-shadow:
                0 8px 16px 0 rgba(0, 0, 0, 0.07),
                0 3px 6px 0 rgba(0, 0, 0, 0.065);
            overflow: hidden;
            margin-left: 20px;
            margin-right: 10px;

            &.close-filter-box {
                display: none;
                text-align: center;

                button {
                    width: 100%;
                    border: none;
                    text-transform: uppercase;
                    outline: none;
                    font-family: inherit;
                    font-weight: bold;
                    padding: 5px 0px;
                    border-bottom: 2px solid;
                    background: white;
                    color: $text-color-accent;
                    cursor: pointer;
                }
            }

            &.select-color {
                ul,
                li {
                    padding: 0;
                    list-style: none;
                    margin: 0;
                }

                li {
                    margin-bottom: 10px;
                }

                .color-box {
                    background: transparent;
                    width: 12px;
                    height: 12px;
                    display: inline-block;
                    margin-right: 10px;
                }
            }

            .title {
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                padding: 15px 20px;
            }
            .content {
                padding: 15px 20px;
            }
        }
    }

    .toggle-filter-box {
        padding: 10px;
        padding-top: 0px;
        text-align: right;
        display: none;

        button {
            border: none;
            text-transform: uppercase;
            outline: none;
            font-family: inherit;
            font-weight: bold;
            padding: 1px 2px;
            border-bottom: 2px solid;
            color: $text-color-accent;
            background: transparent;
            cursor: pointer;
        }
    }

    .list {
        .item {
            display: block;
            width: 25%;
            height: 400px;
            padding: 0 10px;
            padding-bottom: 20px;
            box-sizing: border-box;
            float: left;

            .wrapper {
                box-sizing: border-box;
                height: 100%;
                position: relative;
                cursor: pointer;
                transition: all 0.25s;
                position: relative;

                .love-btn {
                    position: absolute;
                    top: 6px;
                    right: 6px;
                    background: white;
                    color: $text-color-primary;
                    border: none;
                    text-transform: uppercase;
                    outline: none;
                    font-family: inherit;
                    font-weight: bold;
                    padding: 3px 7px;
                }

                .image {
                    box-sizing: border-box;
                    height: 150px;
                    width: 100%;
                    background-color: white;
                    padding-bottom: 10px;

                    .bg {
                        background-color: white;
                        background-size: contain;
                        background-repeat: no-repeat;
                        background-position: center center;
                        width: 100%;
                        height: 100%;
                    }
                }

                .detail {
                    padding-top: 10px;

                    .rate {
                        margin-top: 10px;

                        & > div {
                            margin: 0 auto;
                            display: block;
                            width: 120px;
                        }
                    }

                    .name {
                        text-transform: uppercase;
                        font-weight: bold;
                        text-align: center;
                        padding: 10px;
                        padding-bottom: 5px;
                    }

                    .desc {
                        text-align: center;
                        font-size: 14px;
                        opacity: 0.5;
                    }

                    .price {
                        text-align: center;
                        font-weight: bold;
                        font-size: 22px;
                        padding: 10px;
                        color: $text-color-accent;
                    }
                }

                .buttons {
                    position: absolute;
                    left: 14px;
                    bottom: 14px;
                    right: 14px;

                    button {
                        background: white;
                        color: $text-color-primary;
                        border: none;
                        text-transform: uppercase;
                        outline: none;
                        font-family: inherit;
                        font-weight: bold;
                        padding: 3px 7px;
                    }
                }

                &:hover {
                    box-shadow:
                        0 8px 16px 0 rgba(40, 40, 90, 0.09),
                        0 3px 6px 0 rgba(0, 0, 0, 0.065),
                        0px 10px 0px 0px $text-color-accent;
                }
            }
        }
    }
}

@media (max-width: 1400px) {
    .page-ecommerce-products {
        .list {
            .item {
                width: 33.33%;
            }
        }
    }
}

@media (max-width: 1230px) {
    .page-ecommerce-products {
        .list {
            .item {
                width: 50%;
            }
        }
    }
}

@media (max-width: 1200px) {
    .page-ecommerce-products {
        .sidebar {
            width: 200px;
        }
    }
}

@media (max-width: 940px) {
    .page-ecommerce-products {
        .sidebar {
            width: 230px;
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            margin: 0;
            z-index: 999;
            transform: translateX(-100%);
            transition: all 0.25s;
            background: white;

            .scroller {
                padding: 15px;
                padding-top: 20px;
            }

            .widget {
                margin-left: 5px;
                margin-right: 5px;
                &.close-filter-box {
                    display: block;
                }
            }

            &.open {
                transform: translateX(0%);
                box-shadow: 3px 0px 10px -3px rgba(0, 0, 0, 0.4);
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
        }

        .toggle-filter-box {
            display: block;
        }
    }
}

@media (max-width: 480px) {
    .page-ecommerce-products {
        .list {
            .item {
                width: 100%;
            }
        }
    }
}
</style>
