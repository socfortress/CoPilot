<template>
    <div class="page-ecommerce-shop scrollable only-y">
        <div class="grid-container">
            <div class="widget w1" @click="gotoProducts">
                <div class="bg" style="background-image: url(/static/images/shop-cat/office.jpg)"></div>
                <div class="title">Office</div>
                <div class="desc">
                    <p>Lorem ipsum dolor sit amet.</p>
                    <span class="accent-text"><strong>6374</strong> items</span>
                </div>
            </div>
            <div class="widget w2" @click="gotoProducts">
                <div class="bg" style="background-image: url(/static/images/shop-cat/home.jpg)"></div>
                <div class="title">Home</div>
                <div class="desc">
                    <p>Praesent imperdiet dictum mauris in pharetra.</p>
                    <span class="accent-text"><strong>2385</strong> items</span>
                </div>
            </div>
            <div class="widget w3" @click="gotoProducts">
                <div class="bg" style="background-image: url(/static/images/shop-cat/tech.jpg)"></div>
                <div class="title">Tech</div>
                <div class="desc">
                    <p>Nam auctor ultricies nisi.</p>
                    <span class="accent-text"><strong>2856</strong> items</span>
                </div>
            </div>
            <div class="widget w4" @click="gotoProducts">
                <div class="bg" style="background-image: url(/static/images/shop-cat/watches.jpg)"></div>
                <div class="title">Watches</div>
                <div class="desc">
                    <p>In ante risus, lacinia vel pellentesque.</p>
                    <span class="accent-text"><strong>342</strong> items</span>
                </div>
            </div>
            <div class="widget w5" @click="gotoProducts">
                <div class="bg" style="background-image: url(/static/images/shop-cat/clothing.jpg)"></div>
                <div class="title">Clothing</div>
                <div class="desc">
                    <p>Vivamus quis volutpat leo.</p>
                    <span class="accent-text"><strong>654</strong> items</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "EcommerceShop",
    methods: {
        gotoProducts() {
            this.$router.push({ name: "ecommerce-products" })
        }
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-ecommerce-shop {
    .grid-container {
        display: grid;
        height: 100%;
        grid-template-columns: 1fr 1fr 1fr;
        grid-template-rows: 1fr 1fr 1fr;
        grid-gap: 20px 20px;
        grid-template-areas: "w4 w3 w1" "w5 w3 w1" "w2 w2 w1";
    }

    .w1 {
        grid-area: w1;
    }

    .w2 {
        grid-area: w2;
    }

    .w3 {
        grid-area: w3;
    }

    .w4 {
        grid-area: w4;
    }

    .w5 {
        grid-area: w5;
    }

    .widget {
        min-height: 140px;
        border: 5px solid $text-color-accent;
        position: relative;
        color: $text-color-primary;
        overflow: hidden;
        cursor: pointer;
        border-radius: 4px;

        .bg {
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            right: 0;
            height: 100%;
            widows: 100%;
            background-size: cover;
            background-repeat: no-repeat;
            background-position: center center;
            opacity: 0.8;
            transform: scale(1.06);
            transition: all 0.75s;
        }

        .title {
            background: $text-color-accent;
            display: inline-block;
            color: $background-color;
            padding: 5px 15px;
            padding-top: 0px;
            padding-left: 10px;
            text-transform: uppercase;
            font-weight: bold;
            position: relative;
        }

        .desc {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            padding: 20px;
            box-sizing: border-box;
            transform: translateY(100%);
            opacity: 0;
            transition: all 0.75s;

            .accent-text {
                background: $background-color;
                padding: 2px 10px;
            }
        }

        &:hover {
            .bg {
                opacity: 0.3;
                transform: scale(1.03);
                filter: blur(3px);
            }
            .desc {
                opacity: 1;
                transform: translateY(0%);
            }
        }
    }
}
@media all and (-ms-high-contrast: none) {
    .page-ecommerce-shop {
        .grid-container {
            display: -ms-grid;
            -ms-grid-columns: 1fr 1fr 1fr;
            -ms-grid-rows: 1fr 1fr 1fr;
        }

        .w1 {
            -ms-grid-row: 1;
            -ms-grid-row-span: 3;
            -ms-grid-column: 3;
            -ms-grid-column-span: 1;
        }

        .w2 {
            -ms-grid-row: 3;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 2;
        }

        .w3 {
            -ms-grid-row: 1;
            -ms-grid-row-span: 2;
            -ms-grid-column: 2;
            -ms-grid-column-span: 1;
        }

        .w4 {
            -ms-grid-row: 1;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 1;
        }

        .w5 {
            -ms-grid-row: 2;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 1;
        }
    }
}

@media (max-width: 1000px) {
    .page-ecommerce-shop {
        .grid-container {
            display: grid;
            height: 100%;
            grid-template-columns: 1fr 1fr 1fr;
            grid-template-rows: 1fr 1fr 1fr 1fr;
            grid-gap: 20px 20px;
            grid-template-areas: "w4 w4 w3" "w5 w5 w3" "w2 w2 w2" "w1 w1 w1";
        }

        .w1 {
            grid-area: w1;
        }

        .w2 {
            grid-area: w2;
        }

        .w3 {
            grid-area: w3;
        }

        .w4 {
            grid-area: w4;
        }

        .w5 {
            grid-area: w5;
        }
    }
}
@media all and (-ms-high-contrast: none) and (max-width: 1000px) {
    .page-ecommerce-shop {
        .grid-container {
            display: -ms-grid;
            -ms-grid-columns: 1fr 1fr 1fr;
            -ms-grid-rows: 1fr 1fr 1fr 1fr;
        }

        .w1 {
            -ms-grid-row: 4;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }

        .w2 {
            -ms-grid-row: 3;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }

        .w3 {
            -ms-grid-row: 1;
            -ms-grid-row-span: 2;
            -ms-grid-column: 3;
            -ms-grid-column-span: 1;
        }

        .w4 {
            -ms-grid-row: 1;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 2;
        }

        .w5 {
            -ms-grid-row: 2;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 2;
        }
    }
}

@media (max-width: 768px) {
    .page-ecommerce-shop {
        .grid-container {
            display: grid;
            height: 100%;
            grid-template-columns: 1fr 1fr 1fr;
            grid-template-rows: 1fr 1fr 1fr 1fr 1fr;
            grid-gap: 20px 20px;
            grid-template-areas: "w4 w4 w4" "w5 w5 w5" "w3 w3 w3" "w2 w2 w2" "w1 w1 w1";
        }

        .w4 {
            grid-area: w4;
        }

        .w5 {
            grid-area: w5;
        }

        .w3 {
            grid-area: w3;
        }

        .w2 {
            grid-area: w2;
        }

        .w1 {
            grid-area: w1;
        }
    }
}
@media all and (-ms-high-contrast: none) and (max-width: 768px) {
    .page-ecommerce-shop {
        .grid-container {
            display: -ms-grid;
            -ms-grid-columns: 1fr 1fr 1fr;
            -ms-grid-rows: 1fr 1fr 1fr 1fr 1fr;
        }

        .w4 {
            -ms-grid-row: 1;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }

        .w5 {
            -ms-grid-row: 2;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }

        .w3 {
            -ms-grid-row: 3;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }

        .w2 {
            -ms-grid-row: 4;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }

        .w1 {
            -ms-grid-row: 5;
            -ms-grid-row-span: 1;
            -ms-grid-column: 1;
            -ms-grid-column-span: 3;
        }
    }
}
</style>
