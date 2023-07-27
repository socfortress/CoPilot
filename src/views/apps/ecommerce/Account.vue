<template>
    <el-scrollbar class="page-ecommerce-account">
        <div class="page-header">
            <h1>
                <span>My Account</span>
            </h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ name: 'ecommerce-shop' }">Shop</el-breadcrumb-item>
                <el-breadcrumb-item>My Account</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div>
            <el-tabs v-model="activeTab" class="themed">
                <el-tab-pane label="Dashboard" name="dashboard">
                    <el-row :gutter="20" class="account-tab">
                        <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                            <div class="card-base card-outline p-20 mb-20 widget-profile">
                                <div class="title">Profile</div>
                                <div class="flex">
                                    <div class="avatar">
                                        <img src="../../../assets/images/avatar.jpg" alt="avatar" />
                                    </div>
                                    <div class="box grow flex column justify-center" @click="activeTab = 'profile'">
                                        <div class="name">Aurora Shenton</div>
                                        <div class="since">since <strong>21 Feb 2018</strong></div>
                                    </div>
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                            <div class="card-base card-outline p-20 mb-20 widget-order">
                                <div class="title">Last order</div>
                                <div class="flex">
                                    <div class="photo">
                                        <img src="/static/images/shop/11.jpg" alt="product-photo" />
                                    </div>
                                    <div class="box grow flex column justify-center" @click="activeTab = 'orders'">
                                        <div class="name">Beautifull Seat</div>
                                        <div class="date">
                                            delivery date <strong>{{ deliveryDate }}</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                            <div class="card-base card-outline p-20 mb-20 widget-achievements">
                                <div class="title">Achievements</div>
                                <div class="flex">
                                    <div class="box grow">
                                        <el-tooltip effect="dark" content="10 Orders" placement="top">
                                            <i class="mdi mdi-trophy"></i>
                                        </el-tooltip>
                                    </div>
                                    <div class="box grow">
                                        <el-tooltip effect="dark" content="Certified User" placement="top">
                                            <i class="mdi mdi-check-decagram"></i>
                                        </el-tooltip>
                                    </div>
                                    <div class="box grow">
                                        <el-tooltip effect="dark" content="100 Orders" placement="top">
                                            <i class="mdi mdi-seal"></i>
                                        </el-tooltip>
                                    </div>
                                    <div class="box grow">
                                        <el-tooltip effect="dark" content="Purchase Protection" placement="top">
                                            <i class="mdi mdi-shield-check"></i>
                                        </el-tooltip>
                                    </div>
                                    <div class="box grow">
                                        <el-tooltip effect="dark" content="Premium User" placement="top">
                                            <i class="mdi mdi-star"></i>
                                        </el-tooltip>
                                    </div>
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="12" :md="12" :lg="6" :xl="6">
                            <div class="card-base card-outline p-20 mb-20 widget-address">
                                <div class="title">Billing address</div>
                                <div class="box grow flex column justify-center" @click="activeTab = 'profile'">
                                    <div class="city">Los Angeles</div>
                                    <div class="street">Church Street 23, Block C2</div>
                                </div>
                            </div>
                        </el-col>
                    </el-row>
                </el-tab-pane>
                <el-tab-pane label="Orders" name="orders">
                    <div class="orders-tab">
                        <div class="order-wrapper" v-for="o in orders" :key="o.id">
                            <div class="order card-shadow--small" :class="{ open: o.open }" @click="o.open = !o.open">
                                <div class="flex">
                                    <div class="status">
                                        <el-progress
                                            type="circle"
                                            :percentage="o.status"
                                            :status="o.status === 100 ? 'success' : null"
                                            :width="80"
                                        ></el-progress>
                                    </div>
                                    <div class="info box grow flex column justify-center">
                                        <div class="title flex justify-space-between">
                                            <div class="date">{{ o.date }}</div>
                                            <div class="number">ORDER #{{ o.id }}</div>
                                        </div>
                                        <div class="amount">$ {{ o.amount }}</div>
                                    </div>
                                </div>
                                <div class="detail flex">
                                    <div class="photo">
                                        <img :src="o.photo" />
                                    </div>
                                    <div class="product box grow flex column justify-center">
                                        <div class="product-name">{{ o.product }}</div>
                                        <div class="price">
                                            <span class="unit-price">$ {{ o.price }}</span>
                                            <span class="qnt"> x {{ o.qnt }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </el-tab-pane>
                <el-tab-pane label="Wishlist" name="wishlist">
                    <el-row class="wishlist-box" :gutter="20">
                        <el-col :xs="24" :sm="8" :md="6" :lg="4" :xl="4">
                            <div class="sidebar card-shadow--small">
                                <div class="title flex justify-space-between align-center">
                                    <span>My lists</span>
                                    <el-tooltip effect="dark" content="Add a New Wishlist" placement="top">
                                        <button><i class="mdi mdi-plus"></i></button>
                                    </el-tooltip>
                                </div>
                                <div class="lists">
                                    <ul>
                                        <li class="active"><a>Chairs</a></li>
                                        <li><a>BBQ</a></li>
                                        <li><a>Games</a></li>
                                        <li><a>Tables</a></li>
                                        <li><a>Accessories</a></li>
                                    </ul>
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="16" :md="18" :lg="20" :xl="20">
                            <el-row class="item-list" :gutter="20">
                                <el-col :xs="24" :sm="24" :md="12" :lg="8" :xl="6" v-for="i in wishlist" :key="i.id">
                                    <div class="item mb-20 flex card-shadow--small" @click="gotoProducts">
                                        <div class="photo">
                                            <img :src="i.photo" />
                                        </div>
                                        <div class="box grow flex column justify-center">
                                            <div class="product-name">{{ i.product }}</div>
                                            <div class="price">$ {{ i.price }}</div>
                                        </div>
                                    </div>
                                </el-col>
                            </el-row>
                        </el-col>
                    </el-row>
                </el-tab-pane>
                <el-tab-pane label="Profile" name="profile">
                    <el-row class="profile-box" :gutter="20">
                        <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                            <div class="user-box card-shadow--small">
                                <div class="photo b-rad-8">
                                    <img src="../../../assets/images/avatar.jpg" alt="avatar" />
                                </div>
                                <div class="name">Aurora Shenton</div>
                                <div class="contacts">
                                    <div><i class="mdi mdi-email mr-10"></i> ashenton@mail.com</div>
                                    <div class="mt-10"><i class="mdi mdi-phone mr-10"></i> 579-459-8481</div>
                                </div>
                            </div>
                            <div class="flex achievements-box justify-space-around card-shadow--small">
                                <div class="box">
                                    <el-tooltip effect="dark" content="10 Orders" placement="top">
                                        <i class="mdi mdi-trophy"></i>
                                    </el-tooltip>
                                </div>
                                <div class="box">
                                    <el-tooltip effect="dark" content="Certified User" placement="top">
                                        <i class="mdi mdi-check-decagram"></i>
                                    </el-tooltip>
                                </div>
                                <div class="box">
                                    <el-tooltip effect="dark" content="100 Orders" placement="top">
                                        <i class="mdi mdi-seal"></i>
                                    </el-tooltip>
                                </div>
                                <div class="box">
                                    <el-tooltip effect="dark" content="Purchase Protection" placement="top">
                                        <i class="mdi mdi-shield-check"></i>
                                    </el-tooltip>
                                </div>
                                <div class="box">
                                    <el-tooltip effect="dark" content="Premium User" placement="top">
                                        <i class="mdi mdi-star"></i>
                                    </el-tooltip>
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                            <div class="billing-box card-shadow--small">
                                <div class="title">Billing address</div>
                                <el-row :gutter="10">
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Number</div>
                                            <div class="value">23, Block C2</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">City</div>
                                            <div class="value">Los Angeles</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Street</div>
                                            <div class="value">Church Street</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Postal Code</div>
                                            <div class="value">100065</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">State</div>
                                            <div class="value">CA</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Country</div>
                                            <div class="value">United States</div>
                                        </div>
                                    </el-col>
                                </el-row>
                            </div>
                            <div class="shipping-box card-shadow--small">
                                <div class="title">Shipping address</div>
                                <el-row :gutter="10">
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Number</div>
                                            <div class="value">23, Block C2</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">City</div>
                                            <div class="value">Los Angeles</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Street</div>
                                            <div class="value">Church Street</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Postal Code</div>
                                            <div class="value">100065</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">State</div>
                                            <div class="value">CA</div>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="box">
                                            <div class="key">Country</div>
                                            <div class="value">United States</div>
                                        </div>
                                    </el-col>
                                </el-row>
                            </div>
                        </el-col>
                    </el-row>
                </el-tab-pane>
            </el-tabs>
        </div>
    </el-scrollbar>
</template>

<script>
import dayjs from "dayjs"
import _ from "lodash"
import Chance from "chance"
const chance = new Chance()

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "EcommerceAccount",
    data() {
        return {
            activeTab: "dashboard",
            deliveryDate: dayjs().format("DD MMM"),
            orders: [],
            wishlist: []
        }
    },
    methods: {
        initOrdersData() {
            const year = new Date().getFullYear()

            _.times(50, number => {
                let price = chance.floating({ min: 30, max: 100, fixed: 2 })
                let qnt = chance.integer({ min: 1, max: 5 })
                let amount = price * qnt

                this.orders.push({
                    date: dayjs(chance.date({ year: year })).format("DD MMM YYYY"),
                    amount: _.replace(amount.toFixed(2).toString(), ".", ","),
                    id: "384628" + number,
                    status: number > 5 ? 100 : chance.integer({ min: 0, max: 90 }),
                    open: false,
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    product: chance.sentence({ words: 3 }),
                    qnt,
                    price: _.replace(price.toFixed(2).toString(), ".", ",")
                })
            })
        },
        initWishlistData() {
            _.times(50, number => {
                let price = chance.floating({ min: 30, max: 100, fixed: 2 })

                this.wishlist.push({
                    id: number,
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    product: chance.sentence({ words: 3 }),
                    price: _.replace(price.toFixed(2).toString(), ".", ",")
                })
            })
        },
        gotoProducts() {
            this.$router.push({ name: "ecommerce-products" })
        }
    },
    created() {
        this.initOrdersData()
        this.initWishlistData()
    }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-ecommerce-account {
    .page-header {
        margin-bottom: 20px;
    }

    .account-tab {
        .card-outline {
            min-height: 130px;
            border: 2px solid darken($background-color, 20);

            .title {
                font-size: 16px;
                margin-bottom: 10px;
                font-weight: bold;
                color: $background-color;
                background: darken($background-color, 20);
                display: inline-block;
                display: inline-block;
                position: relative;
                top: -22px;
                margin-left: -20px;
                padding: 4px 10px;
                text-transform: uppercase;
            }
        }

        .widget-profile {
            .avatar {
                width: 70px;

                img {
                    width: 100%;
                }
            }

            .box.grow {
                background: transparentize($text-color-primary, 0.97);
                height: 70px;
                padding: 0 20px;
                box-sizing: border-box;
                cursor: pointer;

                .since {
                    font-size: 12px;
                    opacity: 0.5;
                }

                &:hover {
                    background: transparentize($text-color-primary, 0.8);
                }
            }
        }
        .widget-order {
            .photo {
                width: 70px;

                img {
                    width: 100%;
                }
            }

            .box.grow {
                background: transparentize($text-color-primary, 0.97);
                height: 70px;
                padding: 0 20px;
                box-sizing: border-box;
                cursor: pointer;

                .date {
                    font-size: 12px;
                    opacity: 0.5;
                }

                &:hover {
                    background: transparentize($text-color-primary, 0.8);
                }
            }
        }
        .widget-achievements {
            .box.grow {
                background: transparentize($text-color-primary, 0.97);
                height: 70px;
                line-height: 70px;
                font-size: 30px;
                box-sizing: border-box;
                text-align: center;
            }
        }
        .widget-address {
            .box.grow {
                background: transparentize($text-color-primary, 0.97);
                height: 70px;
                padding: 0px 20px;
                box-sizing: border-box;
                cursor: pointer;

                .street {
                    font-size: 12px;
                    opacity: 0.5;
                }

                &:hover {
                    background: transparentize($text-color-primary, 0.8);
                }
            }
        }
    }

    .orders-tab {
        margin-left: -10px;
        margin-right: -10px;

        .order-wrapper {
            width: 25%;
            float: left;
            padding: 0 10px;
            box-sizing: border-box;

            .order {
                background: white;
                //color: $background-color;
                border-top-left-radius: 40px;
                border-bottom-left-radius: 40px;
                border-top-right-radius: 40px;
                border-bottom-right-radius: 40px;
                margin-bottom: 20px;
                width: 100%;
                height: 80px;
                overflow: hidden;
                cursor: pointer;
                transition: all 0.25s;

                .el-progress {
                    display: block;

                    .el-progress-circle__track {
                        stroke: transparentize($text-color-primary, 0.9);
                    }

                    .el-progress__text {
                        //color: $background-color;
                        font-weight: bold !important;
                        font-size: 16px !important;
                    }

                    &.is-success .el-progress__text {
                        //color: $color-success;
                    }
                }

                .info {
                    padding: 0 20px;

                    .date {
                        font-weight: bold;
                    }

                    .number {
                        opacity: 0.5;
                        font-size: 14px;
                    }

                    .amount {
                        margin-top: 5px;
                        color: $text-color-accent;
                    }
                }

                .detail {
                    padding: 17px 20px;
                    box-sizing: border-box;

                    .photo {
                        width: 60px;

                        img {
                            width: 100%;
                        }
                    }

                    .product-name {
                        box-sizing: border-box;
                        padding-left: 20px;
                        font-weight: bold;
                    }
                    .price {
                        box-sizing: border-box;
                        padding-left: 20px;
                        margin-top: 5px;
                        font-size: 14px;

                        .qnt {
                            opacity: 0.5;
                        }
                    }
                }

                &.open {
                    height: 180px;
                    border-bottom-left-radius: 20px;
                    border-bottom-right-radius: 20px;
                    border-top-right-radius: 20px;
                }
            }
        }
    }

    .wishlist-box {
        .sidebar {
            background: white;
            border-radius: 4px;
            margin-bottom: 20px;

            .title {
                padding: 20px;
                border-bottom: 1px solid transparentize($text-color-primary, 0.9);
                font-weight: bold;

                button {
                    background: transparentize($text-color-primary, 0.9);
                    color: var(--text-color);
                    border: none;
                    border-radius: 4px;
                    outline: none;
                    width: 30px;
                    height: 30px;
                    line-height: 30px;
                    padding: 0;
                    margin: 0;
                    text-align: center;
                    font-size: 20px;
                    cursor: pointer;

                    i:before {
                        transition: all 0.25s;
                    }

                    &:hover {
                        background: transparentize($text-color-primary, 0.8);

                        i:before {
                            transform: rotate(180deg);
                        }
                    }
                }
            }
            .lists {
                padding: 20px;

                ul,
                li {
                    padding: 0;
                    margin: 0;
                    list-style: none;
                }

                li {
                    margin-bottom: 10px;

                    &.active a {
                        color: $text-color-primary;
                    }
                }
            }
        }
        .item-list {
            .item {
                background: white;
                border-radius: 4px;
                overflow: hidden;
                cursor: pointer;

                .photo {
                    width: 70px;
                    padding: 10px;

                    img {
                        width: 100%;
                        display: block;
                    }
                }

                .box {
                    padding: 0 10px;

                    .product-name {
                        font-weight: bold;
                    }
                    .price {
                        color: $text-color-accent;
                    }
                }

                &:hover {
                    background: transparentize($text-color-primary, 0.8);
                }
            }
        }
    }

    .profile-box {
        .user-box {
            background: white;
            border-radius: 4px;
            padding: 20px;
            box-sizing: border-box;
            margin-bottom: 20px;

            .photo {
                width: 200px;
                display: block;
                margin: 10px auto;
                border: 5px solid $text-color-primary;

                img {
                    width: 100%;
                    display: block;
                }
            }
            .name {
                text-align: center;
                font-size: 20px;
                margin: 10px 0;
            }

            .contacts {
                background: transparentize($text-color-primary, 0.97);
                padding: 20px;
            }
        }

        .achievements-box {
            background: white;
            border-radius: 4px;
            padding: 20px;
            box-sizing: border-box;
            margin-bottom: 20px;

            .box {
                padding: 10px;
                //background: transparentize($text-color-primary, .9);
                font-size: 20px;
                min-width: 26px;
                text-align: center;
            }
        }

        .billing-box,
        .shipping-box {
            background: white;
            border-radius: 4px;
            margin-bottom: 20px;
            padding: 20px;

            .title {
                font-weight: bold;
                margin-bottom: 20px;
            }

            .box {
                background: transparentize($text-color-primary, 0.97);
                padding: 20px;
                margin-bottom: 10px;

                .key {
                    font-size: 14px;
                    opacity: 0.7;
                }
            }
        }
    }
}

@media (max-width: 1330px) {
    .page-ecommerce-account {
        .orders-tab {
            .order-wrapper {
                width: 33.33333%;
            }
        }
    }
}
@media (max-width: 1000px) {
    .page-ecommerce-account {
        .orders-tab {
            .order-wrapper {
                width: 50%;
            }
        }
    }
}
@media (max-width: 700px) {
    .page-ecommerce-account {
        .orders-tab {
            .order-wrapper {
                width: 100%;
            }
        }
    }
}
</style>
