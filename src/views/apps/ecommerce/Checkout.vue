<template>
    <div class="page-ecommerce-checkout scrollable only-yt">
        <div class="page-header card-base header-primary">
            <h1>
                <span>Checkout</span>
            </h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ name: 'ecommerce-shop' }">Shop</el-breadcrumb-item>
                <el-breadcrumb-item :to="{ name: 'ecommerce-cart' }">Cart</el-breadcrumb-item>
                <el-breadcrumb-item>Checkout</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="widget shipping card-shadow--small b-rad-4">
            <div class="title">Shipping information</div>
            <div class="content">
                <div class="flex justify-space-between">
                    <div class="box grow flex column mt-40 fs-20 info">
                        <div class="mb-15"><i class="mdi mdi-account mr-10"></i>Aurora Shenton</div>
                        <div class="mb-15"><i class="mdi mdi-map-marker mr-10"></i>Los Angeles, Church Street, 23, Block C2</div>
                        <div><i class="mdi mdi-phone mr-10"></i>579-459-8481</div>
                    </div>

                    <div class="box grow flex mt-40 fs-20 type align-center justify-center">
                        <div class="box grow type-btn text-center">
                            <div><i class="mdi mdi-truck mb-10 fs-30"></i></div>
                            <div><span>Standard</span></div>
                        </div>
                        <div class="box grow type-btn text-center">
                            <div><i class="mdi mdi-airplane mb-10 fs-30"></i></div>
                            <div><span>3 Days</span></div>
                        </div>
                        <div class="box grow type-btn text-center active">
                            <div><i class="mdi mdi-rocket mb-10 fs-30"></i></div>
                            <div><span>1 Day</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="widget review card-shadow--small b-rad-4">
            <div class="title">Review items (5)</div>
            <div class="content">
                <el-row class="items mt-40" :gutter="20">
                    <el-col v-for="i in items" :key="i.id" :xs="24" :sm="12" :md="12" :lg="8" :xl="8">
                        <div class="item mb-20 flex">
                            <div class="photo">
                                <img :src="i.photo" />
                            </div>
                            <div class="box grow flex column justify-center">
                                <div class="product-name">{{ i.product }}</div>
                                <div class="price">
                                    {{ i.qnt }} x $ {{ i.price_text }} = <strong>$ {{ i.amount_text }}</strong>
                                </div>
                            </div>
                        </div>
                    </el-col>
                </el-row>
            </div>
        </div>

        <div class="widget payment card-shadow--small b-rad-4">
            <div class="title">Payment</div>
            <div class="content">
                <div class="flex justify-space-between">
                    <div class="box grow mt-40 pr-30 info">
                        <h3 class="m-0 mb-10">General Info</h3>
                        <p>
                            Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore
                            magna aliqua.
                            <br /><br />
                            Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
                        </p>
                    </div>

                    <div class="box grow flex column mt-40 card">
                        <h3 class="m-0 mb-10">Credit Card</h3>
                        <el-row :gutter="20" class="fs-20">
                            <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="mb-20">
                                <el-input placeholder="Card number" v-model="card" class="themed"></el-input>
                            </el-col>
                            <el-col :xs="12" :sm="12" :md="12" :lg="12" :xl="12" class="mb-20">
                                <el-input placeholder="MM/YY" v-model="date" class="themed"></el-input>
                            </el-col>
                            <el-col :xs="12" :sm="12" :md="12" :lg="12" :xl="12" class="mb-20">
                                <el-input type="password" placeholder="CVC" v-model="cvv" class="themed"></el-input>
                            </el-col>
                            <el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="mb-20">
                                <el-input placeholder="Full name" v-model="name" class="themed"></el-input>
                            </el-col>
                        </el-row>
                    </div>

                    <div class="box grow mt-40 total">
                        <div class="t-row">
                            <div class="label">Total</div>
                            <div class="value">$ {{ price2Text(amount) }}</div>
                        </div>
                        <div class="t-row">
                            <div class="label">Coupan Discount</div>
                            <div class="value">$ 100,00</div>
                        </div>
                        <div class="t-row">
                            <div class="label">Delivery Charges</div>
                            <div class="value">$ 50,00</div>
                        </div>
                        <div class="t-row">
                            <div class="label">Tax</div>
                            <div class="value">$ 100,00</div>
                        </div>
                        <div class="t-row tot">
                            <div class="label">Payable Amount</div>
                            <div class="value">$ {{ price2Text(amount + 50) }}</div>
                        </div>
                        <button>Confirm & Pay</button>
                    </div>
                </div>
            </div>

            <div class="mt-40 small-info">
                <h3 class="m-0 mb-10">General Info</h3>
                <p>
                    Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna
                    aliqua.
                    <br /><br />
                    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
                </p>
            </div>
        </div>
    </div>
</template>

<script>
import Chance from "chance"
const chance = new Chance()
import _ from "lodash"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "EcommerceCheckout",
    data() {
        return {
            items: [],
            amount: 0,
            card: "",
            date: "",
            cvv: "",
            name: ""
        }
    },
    methods: {
        price2Text(price) {
            return _.replace(price.toFixed(2).toString(), ".", ",")
        },
        initItemsData() {
            _.times(5, number => {
                let price = chance.floating({ min: 30, max: 100, fixed: 2 })
                let qnt = chance.integer({ min: 1, max: 5 })
                let amount = price * qnt
                this.amount += amount

                this.items.push({
                    id: number,
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    product: chance.sentence({ words: 3 }),
                    price,
                    price_text: _.replace(price.toFixed(2).toString(), ".", ","),
                    qnt,
                    amount,
                    amount_text: _.replace(amount.toFixed(2).toString(), ".", ",")
                })
            })
        }
    },
    created() {
        this.initItemsData()
    }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-ecommerce-checkout {
    padding-left: 20px;
    padding-right: 15px;

    .page-header {
        margin-bottom: 20px;
    }

    .widget {
        position: relative;
        border: 4px solid $text-color-accent;
        box-sizing: border-box;
        padding: 20px;
        margin-bottom: 20px;
        background: white;

        .title {
            background: $text-color-accent;
            color: $background-color;
            position: absolute;
            top: 0;
            left: 0;
            padding: 2px 12px 6px 8px;
            font-size: 16px;
            font-weight: bold;
            text-transform: uppercase;
        }

        &.shipping {
            .info {
                background: $background-color;
                padding: 30px;
                margin-right: 10px;
                box-sizing: border-box;
            }
            .type {
                background: $background-color;
                margin-left: 10px;
                padding: 30px;
                box-sizing: border-box;

                .type-btn {
                    background: transparentize($text-color-accent, 0.9);
                    border: 1px solid $text-color-accent;
                    color: $text-color-accent;
                    padding: 20px;
                    text-align: center;

                    &.active {
                        background: $text-color-accent;
                        color: white;
                    }
                }
            }
        }

        &.review {
            .items {
                .item {
                    background: transparentize($text-color-primary, 0.97);
                    box-sizing: border-box;

                    .photo {
                        width: 65px;
                        padding: 10px;
                        background: white;

                        img {
                            width: 100%;
                            display: block;
                        }
                    }

                    .box {
                        padding-left: 20px;
                        padding-right: 20px;

                        .product-name {
                            font-size: 16px;
                        }
                        .price {
                            font-size: 14px;
                            margin-top: 2px;
                            color: $text-color-accent;
                        }
                    }

                    &:hover {
                        .photo {
                            .add-btn {
                                opacity: 1;
                            }
                        }
                    }
                }
            }
        }

        &.payment {
            .card {
                max-width: 400px;
            }

            .total {
                text-align: right;
                font-size: 16px;

                .t-row {
                    & > div {
                        display: inline-block;
                    }
                    .label {
                        padding: 5px 10px;
                        opacity: 0.6;
                    }
                    .value {
                        padding: 5px 10px;
                        min-width: 100px;
                        text-align: left;
                    }

                    &.tot {
                        & > div {
                            font-size: 20px;
                            opacity: 1;
                            font-weight: bold;
                            border-top: 1px solid $text-color-primary;
                        }
                    }
                }

                button {
                    background: transparentize($text-color-accent, 0.9);
                    border: 1px solid $text-color-accent;
                    border-radius: 0;
                    color: $text-color-accent;
                    padding: 10px;
                    margin-top: 10px;
                    font-family: inherit;
                    font-size: 20px;
                    font-weight: bold;
                    width: 100%;
                    max-width: 300px;
                    text-align: center;
                    cursor: pointer;

                    &:hover {
                        background: $text-color-accent;
                        color: white;
                    }
                }
            }

            .small-info {
                display: none;
            }
        }
    }
}

@media (max-width: 1100px) {
    .page-ecommerce-checkout {
        .widget {
            &.payment {
                .info {
                    display: none;
                }
                .small-info {
                    display: block;
                }
            }
        }
    }
}
@media (max-width: 850px) {
    .page-ecommerce-checkout {
        .widget {
            &.shipping {
                .content {
                    & > .flex {
                        display: block;
                        clear: both;
                        width: 100%;
                    }
                }

                .info {
                    display: block;
                    clear: both;
                    width: 100%;
                    margin: 0;
                    margin-top: 40px;
                }
                .type {
                    display: block;
                    clear: both;
                    width: 100%;
                    margin: 0;
                }
            }

            &.payment {
                .content {
                    & > .flex {
                        display: block;
                        clear: both;
                        width: 100%;
                    }
                }

                .card {
                    display: block;
                    clear: both;
                    width: 100%;
                    margin: 0 auto;
                    margin-top: 40px;
                }
                .total {
                    display: block;
                    clear: both;
                    width: 100%;
                    margin: 0 auto;
                    margin-top: 20px;
                }
            }
        }
    }
}

@media (max-width: 450px) {
    .page-ecommerce-checkout {
        .widget {
            &.payment {
                .total {
                    font-size: 12px;

                    .t-row {
                        .value {
                            min-width: inherit;
                        }
                        &.tot {
                            & > div {
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
