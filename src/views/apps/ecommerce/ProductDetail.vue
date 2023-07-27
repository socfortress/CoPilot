<template>
    <div class="page-ecommerce-product-detail scrollable only-y">
        <el-breadcrumb separator="/" class="themed">
            <el-breadcrumb-item :to="{ name: 'ecommerce-shop' }">Shop</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ name: 'ecommerce-shop' }">Office</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ name: 'ecommerce-products' }">Chairs</el-breadcrumb-item>
            <el-breadcrumb-item>Beautifull Seat</el-breadcrumb-item>
        </el-breadcrumb>

        <el-row class="mt-30">
            <el-col>
                <div class="item-box card-shadow--medium">
                    <el-row>
                        <el-col :xs="24" :sm="12" :md="12" :lg="8" :xl="8">
                            <div class="gallery-box">
                                <div class="main-photo">
                                    <img src="/static/images/shop/2.jpg" data-zoom="/static/images/shop/2.jpg" />
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="12" :md="12" :lg="16" :xl="16">
                            <div class="detail-box">
                                <h1 class="title">Beautifull Seat</h1>
                                <div class="rate">
                                    <el-rate
                                        v-model="rate"
                                        style="width: 120px; display: inline-block; margin-right: 10px"
                                        disabled
                                    ></el-rate>
                                    <span class="review fs-12 o-050">(5 customer review)</span>
                                </div>
                                <div class="price-box">
                                    <span class="discounted-price">$ 637,24</span>
                                    <span class="normal-price">$ 937,78</span>
                                    <span class="discount">28% off</span>
                                </div>
                                <div class="description">
                                    Lorem Ipsum available, but the majority have suffered alteration in some form, by injected humour, or
                                    randomised words which don't look even slightly believable. but the majority have suffered alteration in
                                    some form, by injected humour.
                                </div>
                                <div class="actions-box">
                                    <el-button class="themed mr-10 mb-10" type="primary" plain>
                                        <i class="mdi mdi-cart-outline"></i> Add to Cart
                                    </el-button>
                                    <el-button class="themed mb-10 ml-0" type="primary" plain>
                                        <i class="mdi mdi-heart-outline"></i> Add to Wishlist
                                    </el-button>
                                </div>
                            </div>
                        </el-col>
                    </el-row>
                </div>
            </el-col>
        </el-row>

        <el-row class="mt-20">
            <el-col>
                <div class="item-box p-30">
                    <el-tabs v-model="activeTab" class="themed">
                        <el-tab-pane label="Description" name="description">
                            <p>
                                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam porttitor, nibh vel imperdiet pretium, augue ex
                                rutrum sapien, sit amet rutrum purus libero pretium justo. Curabitur id nisi vitae metus ultricies
                                condimentum. Fusce semper justo ipsum, rutrum rhoncus nulla scelerisque id. Lorem ipsum dolor sit amet,
                                consectetur adipiscing elit. Donec tempor nisl ornare ipsum ultricies, nec fermentum sem tincidunt. Donec
                                arcu purus, tincidunt sed urna a, tristique gravida arcu. Nam ac tincidunt felis. Nam pulvinar ante ut
                                efficitur pellentesque. Cras vel sodales turpis. Nunc fermentum sed sem quis egestas. Nullam ultrices eu
                                diam quis viverra. Proin nec convallis risus. Maecenas efficitur dolor quis lacus scelerisque, vel rutrum
                                nibh vestibulum. Nullam ante lorem, faucibus at convallis ut, ullamcorper sed lacus. In finibus orci eu nibh
                                venenatis, imperdiet rhoncus felis accumsan. Cras a augue bibendum, consectetur enim mattis, vulputate leo.
                            </p>
                            <p>
                                Mauris vel facilisis tellus, sit amet cursus turpis. Duis ut consectetur nunc. Nulla viverra nulla vel mi
                                pellentesque efficitur. Cras sit amet efficitur magna. Vestibulum ac ante ac magna feugiat scelerisque.
                                Nullam condimentum gravida euismod. Donec rutrum egestas massa. Morbi venenatis dolor ac felis efficitur
                                finibus. Vestibulum sed pellentesque sapien. Donec a rutrum leo, at ornare ligula. Nullam vel feugiat
                                turpis, ac porta felis. Mauris hendrerit tincidunt ante sit amet vestibulum. Cras efficitur porta vulputate.
                            </p>
                            <p>
                                Curabitur auctor lacus eget lorem blandit, ac tempus ante euismod. Morbi nec odio in sem elementum hendrerit
                                id vel ipsum. In nec nibh vel orci porta pretium. Pellentesque habitant morbi tristique senectus et netus et
                                malesuada fames ac turpis egestas. Cras nec tristique diam, ac vulputate massa. Aliquam massa magna,
                                tincidunt et ultrices tempor, scelerisque nec sem. Sed auctor faucibus facilisis. Nulla vel ligula non
                                mauris lobortis pretium. Donec sit amet volutpat nisl, sed ultrices turpis. Curabitur posuere erat nunc,
                                eget volutpat turpis aliquet quis.
                            </p>
                        </el-tab-pane>
                        <el-tab-pane label="Aditional information" name="info">
                            <p>
                                Curabitur auctor lacus eget lorem blandit, ac tempus ante euismod. Morbi nec odio in sem elementum hendrerit
                                id vel ipsum. In nec nibh vel orci porta pretium. Pellentesque habitant morbi tristique senectus et netus et
                                malesuada fames ac turpis egestas. Cras nec tristique diam, ac vulputate massa. Aliquam massa magna,
                                tincidunt et ultrices tempor, scelerisque nec sem. Sed auctor faucibus facilisis. Nulla vel ligula non
                                mauris lobortis pretium. Donec sit amet volutpat nisl, sed ultrices turpis. Curabitur posuere erat nunc,
                                eget volutpat turpis aliquet quis.
                            </p>
                            <p>
                                Ut posuere felis et ante pharetra ullamcorper. Maecenas sagittis nisl ac est porta volutpat. Praesent et
                                mollis lorem, vel egestas augue. Aenean euismod auctor dapibus. Nullam sit amet urna erat. Duis euismod diam
                                et nisl molestie dapibus. Sed non ligula vitae risus lacinia viverra id tempor neque. Sed tincidunt
                                ultricies lacinia. Sed sed elit commodo, mattis mauris sed, imperdiet urna. Donec eu interdum ligula. In leo
                                risus, vulputate sed diam nec, porta facilisis elit. Praesent sed sapien ultrices, vulputate nisl a,
                                placerat nulla. Fusce mollis lectus orci. Pellentesque ut enim eleifend lacus dapibus vehicula. Sed mi
                                neque, ullamcorper euismod diam quis, aliquet ultricies eros.
                            </p>
                            <p>
                                Pellentesque nunc purus, ultrices vitae nisi id, placerat mollis leo. Aenean egestas orci vel ipsum eleifend
                                dapibus. Suspendisse a pellentesque dui, eu sodales massa. Donec condimentum arcu vitae augue consequat, in
                                sodales enim scelerisque. Sed sodales eros sed porta cursus. Ut pellentesque bibendum tincidunt. Donec a
                                molestie risus, eget consectetur nulla. Sed sed diam erat. Vestibulum velit ligula, eleifend eget sem ut,
                                tristique sagittis neque. Phasellus eget velit nisi. Ut finibus ligula eget lectus aliquet, a ullamcorper
                                velit facilisis.
                            </p>
                        </el-tab-pane>
                        <el-tab-pane label="Reviews (0)" name="reviews"> Leave a review </el-tab-pane>
                    </el-tabs>
                </div>
            </el-col>
        </el-row>
    </div>
</template>

<script>
import Drift from "drift-zoom"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "EcommerceProductDetail",
    data() {
        return {
            rate: 4,
            qnt: 1,
            activeTab: "description"
        }
    },
    mounted() {
        const mainPhoto = document.querySelector(".main-photo img")
        const paneContainer = document.querySelector(".main-photo")

        new Drift(mainPhoto, {
            paneContainer: paneContainer,
            inlinePane: false,
            zoomFactor: 2
        })
    }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-ecommerce-product-detail {
    padding: 0 20px;

    .item-box {
        border-radius: 4px;
        overflow: hidden;

        .main-photo {
            position: relative;
            overflow: hidden;
            background: white;
            padding: 30px;

            img {
                width: 100%;
            }
        }
        .detail-box {
            padding: 30px;
            position: relative;

            .title {
                margin: 0;
            }

            .price-box {
                margin-top: 20px;
                margin-bottom: 30px;

                .discounted-price {
                    color: $text-color-accent;
                    font-weight: bold;
                    font-size: 25px;
                    margin-right: 20px;
                    display: inline-block;
                }
                .normal-price {
                    opacity: 0.5;
                    text-decoration: line-through;
                    text-decoration-color: $text-color-accent;
                    margin-right: 10px;
                    display: inline-block;
                }
                .discount {
                    color: $text-color-accent;
                    display: inline-block;
                }
            }

            .actions-box {
                margin-top: 30px;

                .el-input-number {
                    width: 100px;

                    .el-input__inner {
                        color: $text-color-accent;
                        background-color: transparent;
                        border-color: $text-color-accent;
                        font-family: inherit;
                        font-weight: bold;
                        padding-left: 5px;
                        padding-right: 45px;
                    }
                }

                .el-button {
                    font-family: inherit;
                    margin-left: 0;
                }
            }
        }
    }
}
</style>
