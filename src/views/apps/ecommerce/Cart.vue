<template>
    <el-scrollbar class="page-ecommerce-cart">
        <el-row class="cart-box" :gutter="20">
            <el-col :xs="24" :sm="16" :md="18" :lg="18" :xl="18">
                <el-row class="item-list">
                    <el-col>
                        <div class="item mb-20 page-header card-base header-primary">
                            <h1>
                                <span>Your Cart (5 items)</span>
                            </h1>
                            <el-breadcrumb separator="/" class="mt-10 themed">
                                <el-breadcrumb-item :to="{ name: 'ecommerce-shop' }">Shop</el-breadcrumb-item>
                                <el-breadcrumb-item>Cart</el-breadcrumb-item>
                            </el-breadcrumb>
                        </div>
                    </el-col>
                    <el-col v-for="i in cart" :key="i.id">
                        <div class="item mb-20 flex card-shadow--small b-rad-4">
                            <div class="photo">
                                <img :src="i.photo" />
                            </div>
                            <div class="box grow flex column justify-center">
                                <div class="product-name">{{ i.product }}</div>
                                <div class="price">$ {{ i.price_text }}</div>
                            </div>
                            <div class="box grow flex center text-center">
                                <div>
                                    <span class="ics">X</span>
                                    <el-input-number
                                        v-model="i.qnt"
                                        controls-position="right"
                                        :min="1"
                                        class="themed ml-10"
                                    ></el-input-number>
                                </div>
                            </div>
                            <div class="box grow flex align-center">
                                <div class="text-right box grow">
                                    <button class="del-btn"><i class="mdi mdi-delete"></i></button>
                                </div>
                            </div>
                        </div>
                    </el-col>
                </el-row>
            </el-col>

            <el-col :xs="24" :sm="8" :md="6" :lg="6" :xl="6">
                <div class="widget card-shadow--small b-rad-4">
                    <div class="title flex justify-space-between align-center">Total</div>
                    <div class="content">
                        <div class="fs-30">$ {{ amount_text }}</div>
                        <button @click="gotoCheckout">Checkout</button>
                    </div>
                </div>
                <div class="widget card-shadow--small b-rad-4">
                    <div class="title flex justify-space-between align-center">Related Products</div>
                    <div class="content">
                        <el-row class="items">
                            <el-col v-for="i in items" :key="i.id">
                                <div class="item mb-20 flex">
                                    <div class="photo">
                                        <div class="add-btn"><i class="mdi mdi-plus-circle"></i></div>
                                        <img :src="i.photo" />
                                    </div>
                                    <div class="box grow flex column justify-center">
                                        <div class="product-name">{{ i.product }}</div>
                                        <div class="price">$ {{ i.price }}</div>
                                    </div>
                                </div>
                            </el-col>
                        </el-row>
                    </div>
                </div>
                <div class="widget card-shadow--small b-rad-4">
                    <div class="title flex justify-space-between align-center">Support</div>
                    <div class="content">
                        <div>
                            <div><i class="mdi mdi-email mr-10"></i> shop@mail.com</div>
                            <div class="mt-10"><i class="mdi mdi-phone mr-10"></i> 579-459-8481</div>
                        </div>
                    </div>
                </div>
            </el-col>
        </el-row>
    </el-scrollbar>
</template>

<script>
import Chance from "chance"
const chance = new Chance()
import _ from "lodash"
import { defineComponent } from "vue"

export default defineComponent({
    name: "EcommerceCart",
    data() {
        return {
            items: [],
            cart: []
        }
    },
    computed: {
        amount() {
            return _.reduce(this.cart, (sum, obj) => sum + obj.price * obj.qnt, 0)
        },
        amount_text() {
            return _.replace(this.amount.toFixed(2).toString(), ".", ",")
        }
    },
    methods: {
        gotoCheckout() {
            this.$router.push({ name: "ecommerce-checkout" })
        },
        initCartData() {
            _.times(5, number => {
                let price = chance.floating({ min: 30, max: 100, fixed: 2 })
                let qnt = chance.integer({ min: 1, max: 5 })

                this.cart.push({
                    id: number,
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    product: chance.sentence({ words: 3 }),
                    price,
                    price_text: _.replace(price.toFixed(2).toString(), ".", ","),
                    qnt
                })
            })
        },
        initItemsData() {
            _.times(5, number => {
                let price = chance.floating({ min: 30, max: 100, fixed: 2 })

                this.items.push({
                    id: number,
                    photo: "/static/images/shop/" + chance.integer({ min: 0, max: 19 }) + ".jpg",
                    product: chance.sentence({ words: 3 }),
                    price: _.replace(price.toFixed(2).toString(), ".", ",")
                })
            })
        }
    },
    created() {
        this.initCartData()
        this.initItemsData()
    }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-ecommerce-cart {
    .cart-box {
        .widget {
            background: white;
            margin-bottom: 20px;

            .title {
                padding: 20px;
                border-bottom: 1px solid transparentize($text-color-primary, 0.9);
                font-weight: bold;
            }
            .content {
                padding: 20px;

                button {
                    margin-top: 10px;
                    border: 1px solid $text-color-accent;
                    color: $text-color-accent;
                    background-color: transparentize($text-color-accent, 0.9);
                    padding: 10px;
                    width: 100%;
                    text-align: center;
                    font-family: inherit;
                    font-size: 20px;
                    cursor: pointer;
                    border-radius: 4px;

                    &:hover {
                        background-color: transparentize($text-color-accent, 0.7);
                    }
                }

                .items {
                    .item {
                        background: transparentize($text-color-primary, 0.97);
                        box-sizing: border-box;

                        .photo {
                            width: 58px;
                            position: relative;
                            padding: 10px;
                            background: white;

                            .add-btn {
                                position: absolute;
                                background: transparentize($text-color-accent, 0.3);
                                color: white;
                                top: 0;
                                left: 0;
                                right: 0;
                                bottom: 0;
                                width: 100%;
                                height: 100%;
                                text-align: center;
                                line-height: 78px;
                                font-size: 40px;
                                opacity: 0;
                                transition: all 0.25s;
                            }

                            img {
                                width: 100%;
                                display: block;
                            }
                        }

                        .box {
                            padding-left: 10px;

                            .product-name {
                                font-size: 14px;
                            }
                            .price {
                                font-size: 12px;
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
        }

        .item-list {
            .item {
                background: white;
                padding: 30px;
                box-sizing: border-box;
                margin-bottom: 20px;

                .photo {
                    width: 100px;
                    padding: 10px;
                    background: white;

                    img {
                        width: 100%;
                        display: block;
                    }
                }

                .box {
                    padding-left: 30px;

                    .product-name {
                        font-weight: bold;
                        font-size: 20px;
                    }
                    .price {
                        margin-top: 10px;
                        color: $text-color-accent;
                    }

                    .el-input-number {
                        width: 90px;
                    }

                    .del-btn {
                        margin-top: 10px;
                        color: $text-color-danger;
                        padding: 10px;
                        text-align: center;
                        font-family: inherit;
                        font-size: 20px;
                        cursor: pointer;
                        opacity: 0.5;
                        border: none;
                        background: transparent;
                        outline: none;
                        visibility: hidden;

                        &:hover {
                            opacity: 1;
                        }
                    }
                }

                &:hover {
                    .del-btn {
                        visibility: visible;
                    }
                }
            }
        }
    }
}

@media (max-width: 900px) {
    .page-ecommerce-cart {
        .cart-box {
            .item-list {
                .item {
                    .photo {
                        display: none;
                    }
                    & > .box {
                        padding: 0;
                    }
                }
            }
        }
    }
}

@media (max-width: 600px) {
    .page-ecommerce-cart {
        .cart-box {
            .item-list {
                .item {
                    display: block;
                    padding: 20px;

                    .photo,
                    & > .box {
                        margin-bottom: 10px;
                        width: 100%;
                        display: block;
                        clear: both;
                        padding: 0;
                    }
                }
            }
        }
    }
}
</style>
