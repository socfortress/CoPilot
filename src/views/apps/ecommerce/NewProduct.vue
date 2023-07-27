<template>
    <el-scrollbar class="page-ecommerce-new-product">
        <div class="page-header card-base header-accent">
            <h1>
                <span>Ecommerce new product</span>
            </h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item :to="{ path: '/ecommerce' }">Ecommerce</el-breadcrumb-item>
                <el-breadcrumb-item>New Product</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <el-row>
            <el-col>
                <div class="item-box card-shadow--small b-rad-4">
                    <el-row>
                        <el-col :xs="24" :sm="12" :md="12" :lg="8" :xl="8">
                            <div class="gallery-box">
                                <div class="main-photo">
                                    <div class="btn-close"><i class="mdi mdi-close"></i></div>
                                    <img src="/static/images/shop/2.jpg" />
                                </div>
                                <div class="other-photos">
                                    <div class="a-photo">
                                        <div class="btn-close"><i class="mdi mdi-close"></i></div>
                                        <img src="/static/images/shop/2.jpg" />
                                    </div>
                                    <div class="a-photo">
                                        <div class="btn-close"><i class="mdi mdi-close"></i></div>
                                        <img src="/static/images/shop/2.jpg" />
                                    </div>
                                    <div class="a-photo">
                                        <div class="add-photo">
                                            <div class="dashed-box"></div>
                                            <i class="mdi mdi-image-plus"></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </el-col>
                        <el-col :xs="24" :sm="12" :md="12" :lg="16" :xl="16">
                            <div class="detail-box">
                                <el-row>
                                    <el-col>
                                        <input class="title" v-model="title" placeholder="Product name" />
                                    </el-col>
                                </el-row>
                                <el-row>
                                    <el-col :xs="24" :sm="24" :md="8" :lg="8" :xl="8">
                                        <div class="number-input">
                                            <label>Price ($)</label>
                                            <el-input-number
                                                v-model="price"
                                                controls-position="right"
                                                :min="1"
                                                class="themed mr-10 mb-10"
                                            ></el-input-number>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="24" :md="8" :lg="8" :xl="8">
                                        <div class="number-input">
                                            <label>Discount (%)</label>
                                            <el-input-number
                                                v-model="discount"
                                                controls-position="right"
                                                :min="1"
                                                class="themed mr-10 mb-10"
                                            ></el-input-number>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="24" :md="8" :lg="8" :xl="8">
                                        <div class="number-input">
                                            <label>Stock</label>
                                            <el-input-number
                                                v-model="stock"
                                                controls-position="right"
                                                :min="1"
                                                class="themed mr-10 mb-10"
                                            ></el-input-number>
                                        </div>
                                    </el-col>
                                </el-row>
                                <el-row>
                                    <el-col class="final-price">
                                        final price: <strong>$ {{ finalPrice }}</strong
                                        >, discount: <strong>$ {{ discountPrice }}</strong>
                                    </el-col>
                                </el-row>
                                <el-row>
                                    <el-col class="description-box">
                                        <textarea-autosize
                                            v-model="description"
                                            placeholder="Description"
                                            :min-height="100"
                                        ></textarea-autosize>
                                    </el-col>
                                </el-row>
                                <el-row :gutter="20">
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="select-box mb-10">
                                            <el-select
                                                v-model="cat"
                                                placeholder="Category"
                                                clearable
                                                class="themed"
                                                :popper-class="'themed color-accent-' + colorAccent"
                                            >
                                                <el-option
                                                    v-for="(i, index) in cat_list"
                                                    :key="index"
                                                    :label="i"
                                                    :value="kebabCase(i)"
                                                ></el-option>
                                                <el-option :label="'Cat 2'" :value="'cat2'"></el-option>
                                                <el-option :label="'Cat 3'" :value="'cat3'"></el-option>
                                            </el-select>
                                        </div>
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="12" :lg="12" :xl="12">
                                        <div class="select-box mb-10">
                                            <el-select
                                                v-model="tags"
                                                multiple
                                                filterable
                                                allow-create
                                                default-first-option
                                                placeholder="Tags"
                                                class="themed"
                                                :popper-class="'themed color-accent-' + colorAccent"
                                            >
                                                <el-option
                                                    v-for="item in tags_options"
                                                    :key="item.value"
                                                    :label="item.label"
                                                    :value="item.value"
                                                ></el-option>
                                            </el-select>
                                        </div>
                                    </el-col>
                                </el-row>

                                <el-row class="mt-50">
                                    <el-col class="text-right">
                                        <el-radio-group v-model="status" class="themed">
                                            <el-radio-button label="In Stock"></el-radio-button>
                                            <el-radio-button label="Awaiting"></el-radio-button>
                                            <el-radio-button label="Out of Stock"></el-radio-button>
                                        </el-radio-group>
                                    </el-col>
                                </el-row>

                                <el-row>
                                    <el-col>
                                        <div class="actions-box text-right">
                                            <el-switch
                                                v-model="active"
                                                active-text="Active"
                                                inactive-text=""
                                                class="mr-20 themed"
                                            ></el-switch>
                                            <el-button class="themed mb-10 mr-10" type="primary" plain
                                                ><i class="mdi mdi-content-save"></i> Save</el-button
                                            >
                                            <el-button class="themed mb-10" type="primary" plain
                                                ><i class="mdi mdi-refresh"></i> Reset</el-button
                                            >
                                        </div>
                                    </el-col>
                                </el-row>
                            </div>
                        </el-col>
                    </el-row>
                </div>
            </el-col>
        </el-row>

        <el-row class="mt-20">
            <el-col>
                <div class="item-box p-30 card-shadow--small b-rad-4">
                    <el-row>
                        <el-col>
                            <div class="meta-form">
                                <h3 class="m-0">Meta data</h3>
                                <el-row class="mt-30" :gutter="20">
                                    <el-col :xs="24" :sm="12" :md="6" :lg="4" :xl="4">
                                        <input placeholder="Key" />
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="6" :lg="8" :xl="8">
                                        <input placeholder="Value" />
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="6" :lg="8" :xl="8">
                                        <input placeholder="Description" />
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="6" :lg="4" :xl="4">
                                        <button><i class="mdi mdi-plus-box mr-10 fs-20"></i>add meta</button>
                                    </el-col>
                                </el-row>
                                <el-row class="mt-10" :gutter="20" v-for="i in meta" :key="i.id">
                                    <el-col :xs="24" :sm="12" :md="6" :lg="4" :xl="4">
                                        <input placeholder="Key" v-model="i.title" />
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="6" :lg="8" :xl="8">
                                        <input placeholder="Value" v-model="i.keywords" />
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="6" :lg="8" :xl="8">
                                        <input placeholder="Description" v-model="i.description" />
                                    </el-col>
                                    <el-col :xs="24" :sm="12" :md="6" :lg="4" :xl="4">
                                        <button><i class="mdi mdi-close-box mr-10 fs-20"></i>delete</button>
                                    </el-col>
                                </el-row>
                            </div>
                        </el-col>
                    </el-row>
                </div>
            </el-col>
        </el-row>
    </el-scrollbar>
</template>

<script>
import _ from "lodash"
import { useMainStore } from "@/stores/main"
import TextareaAutosize from "@/components/TextareaAutosize.vue"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "EcommerceNewProduct",
    data() {
        return {
            discount: 15,
            price: 155,
            stock: 100,
            tags_options: [
                {
                    value: "Chairs",
                    label: "Chairs"
                },
                {
                    value: "Foldable",
                    label: "Foldable"
                },
                {
                    value: "Garden",
                    label: "Garden"
                }
            ],
            tags: [],
            title: "",
            description: "",
            cat: "bar-stools",
            cat_list: [
                "Dining chairs",
                "Foldable chairs",
                "Bar Stools",
                "Garden chairs",
                "Step stools",
                "Junior chairs",
                "High chairs",
                "Fabric armchairs",
                "Leather armchairs",
                "Rattan armchairs",
                "Swivel chairs",
                "Office chairs"
            ],
            status: "Awaiting",
            active: true,
            meta: [
                {
                    id: 0,
                    title: "Brand",
                    keywords: "Stellar",
                    description: ""
                },
                {
                    id: 1,
                    title: "Seat Lock Included",
                    keywords: "Yes",
                    description: ""
                },
                {
                    id: 2,
                    title: "Type",
                    keywords: "Office Chair",
                    description: ""
                },
                {
                    id: 3,
                    title: "Style",
                    keywords: "Contemporary & Modern",
                    description: ""
                }
            ]
        }
    },
    computed: {
        finalPrice() {
            return (this.price - this.discountPrice).toFixed(2)
        },
        discountPrice() {
            return ((this.price / 100) * this.discount).toFixed(2)
        },
        colorAccent() {
            return useMainStore().colorAccent
        }
    },
    methods: {
        kebabCase: _.kebabCase
    },
    components: { TextareaAutosize }
})
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-ecommerce-new-product {
    .page-header {
        margin-bottom: 20px;
    }

    .item-box {
        background: white;

        .main-photo,
        .a-photo {
            position: relative;

            img {
                width: 100%;
            }

            .btn-close {
                position: absolute;
                right: 30px;
                top: 30px;
                background: rgba(0, 0, 0, 0.1);
                width: 20px;
                height: 20px;
                text-align: center;
                line-height: 20px;
            }
        }

        .main-photo {
            padding: 30px;
            box-sizing: border-box;
        }
        .other-photos {
            padding: 0 15px;
            padding-bottom: 15px;
            box-sizing: border-box;

            .a-photo {
                width: 33.3333333%;
                box-sizing: border-box;
                padding: 0 15px;
                display: inline-block;

                .btn-close {
                    position: absolute;
                    right: 15px;
                    top: 0px;
                }

                .add-photo {
                    width: 100%;
                    height: 100%;
                    box-sizing: border-box;
                    padding-bottom: 100%;
                    position: relative;

                    .dashed-box {
                        border: 4px dashed transparentize($text-color-accent, 0.5);
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                    }

                    .mdi {
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        font-size: 30px;
                        transform: translateX(-50%) translateY(-50%);
                        opacity: 0.7;
                    }
                }
            }
        }

        .detail-box {
            padding: 30px;
            padding-left: 0;

            .title {
                background: transparent;
                font-size: 30px;
                border: none;
                outline: none;
                border-bottom: 2px solid transparentize($text-color-primary, 0.8);
                font-family: inherit;
                width: 100%;
                margin-bottom: 20px;
                color: $text-color-primary;
                font-weight: bold;
            }

            .number-input {
                margin-bottom: 10px;

                label {
                    display: block;
                    clear: both;
                    opacity: 0.5;
                    margin-bottom: 10px;
                    font-size: 14px;
                }
            }

            .final-price {
                color: transparentize($text-color-primary, 0.3);

                strong {
                    color: $text-color-accent;
                }
            }

            .description-box {
                margin-top: 20px;
                margin-bottom: 10px;

                textarea {
                    border: 1px solid transparentize($text-color-accent, 0.7);
                    outline: none;
                    width: 100%;
                    resize: vertical;
                    background: white;
                    font-family: inherit;
                    padding: 10px;
                    box-sizing: border-box;
                    color: $text-color-primary;
                    font-size: 16px;
                    border-radius: 4px;
                }
            }

            .el-input-number {
                width: 90px;

                .el-input__inner {
                    color: $text-color-accent;
                    background-color: transparent;
                    border-color: transparentize($text-color-accent, 0.7);
                    font-family: inherit;
                    font-weight: bold;
                }
            }

            .el-button {
                font-family: inherit;
                margin-left: 0;
            }

            .select-box {
                box-sizing: border-box;
            }

            .el-select {
                width: 100%;

                .el-input__inner {
                    border-color: transparentize($text-color-accent, 0.7);
                    color: $text-color-accent;
                    font-family: inherit;
                }
            }

            .actions-box {
                text-align: right;
                margin-top: 20px;
            }

            .el-radio-group {
                .el-radio-button__inner {
                    background-color: transparentize($text-color-accent, 0.9);
                    border-color: transparentize($text-color-accent, 0.7);
                    color: $text-color-accent;
                }
                .el-radio-button__orig-radio:checked + .el-radio-button__inner {
                    background-color: $text-color-accent;
                    color: white;
                }
            }
        }

        .meta-form {
            input,
            button {
                border: 1px solid transparentize($text-color-accent, 0.7);
                outline: none;
                border-radius: 4px;
                color: $text-color-primary;
                padding: 8px 13px;
                background: white;
                width: 100%;
                margin-bottom: 7px;
                box-sizing: border-box;
                font-family: inherit;
                font-size: 14px;
            }

            button {
                cursor: pointer;
                border-bottom: 1px solid $text-color-accent;
                font-family: inherit;
                text-transform: uppercase;
                line-height: 0;
                padding: 16px 2px;
                color: $text-color-accent;

                i {
                    position: relative;
                    top: 3px;
                }
            }
        }
    }
}

@media (max-width: 768px) {
    .page-ecommerce-new-product {
        .item-box {
            .detail-box {
                padding-left: 30px;
            }
        }
    }
}
</style>
