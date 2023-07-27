<template>
    <div class="page-table column scrollable only-y" :class="{ flex: !isMobile, overflow: isMobile }">
        <div class="page-header">
            <h1>V2 Table</h1>
            <h4>for a better experience on Mac OS during horizontal scroll is prefered disable the "Swipe between pages" option</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Tables</el-breadcrumb-item>
                <el-breadcrumb-item>V2 Table</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="toolbar-box flex">
            <div class="search-box box grow">
                <div><i class="mdi mdi-magnify"></i></div>
                <input v-model="search" placeholder="Search..." />
            </div>
            <div class="pagination-box">
                <div class="select-box">
                    <el-select v-model="paginationInfo.pageSize" placeholder="Rows per page" size="small">
                        <el-option value="10" label="10"></el-option>
                        <el-option value="15" label="15"></el-option>
                        <el-option value="20" label="20"></el-option>
                        <el-option value="30" label="30"></el-option>
                        <el-option value="50" label="50"></el-option>
                        <el-option value="100" label="100"></el-option>
                    </el-select>
                </div>
                <div class="label">/page</div>
            </div>
            <div class="csv-box">
                <button @click="downloadCSV">download csv ({{ total }})</button>
            </div>
            <div class="">
                <a href="https://github.com/dwqs/v2-table" target="_blank"><i class="mdi mdi-link-variant"></i> reference</a>
            </div>
        </div>

        <resize-observer @notify="handleResize" />

        <div class="table-box card-base card-shadow--medium box grow" id="table-wrapper" v-loading="!asyncComponent">
            <div :style="{ width: width + 'px' }">
                <!-- v2-table -->
                <component
                    :is="asyncComponent"
                    ref="table"
                    :data="listInPage"
                    :height="height"
                    :border="false"
                    :total="total"
                    :lazy-load="false"
                    :loading="loading"
                    class="styled"
                    :class="{ mobile: isMobile }"
                    @page-change="handlePageChange"
                    :pagination-info="paginationInfo"
                    :default-sort="{ prop: sortingProp, order: sortingOrder }"
                    @sort-change="handleSortChange"
                    @select-change="handleSelectChange"
                    :show-summary="showSummary"
                    :shown-pagination="shownPagination"
                >
                    <v2-table-column type="selection" width="45"></v2-table-column>
                    <v2-table-column label="Name" prop="full_name" sortable width="200" align="left" :fixed="isMobile ? '' : 'left'">
                        <template slot-scope="row">
                            <span class="sel-string" v-html="$options.filters.selected(row.full_name, search)"></span>
                        </template>
                    </v2-table-column>
                    <v2-table-column
                        label="Birthday"
                        prop="birth_day"
                        sortable
                        width="100"
                        :fixed="isMobile ? '' : 'right'"
                    ></v2-table-column>
                    <v2-table-column label="Email" prop="email" sortable width="250">
                        <template slot-scope="row">
                            <span class="sel-string" v-html="$options.filters.selected(row.email, search)"></span>
                        </template>
                    </v2-table-column>
                    <v2-table-column label="Gender" prop="gender" sortable></v2-table-column>
                    <v2-table-column label="Job title" prop="job_title" sortable width="200"></v2-table-column>
                    <v2-table-column label="Company" prop="company" sortable width="120"></v2-table-column>
                    <v2-table-column label="City" prop="city" sortable width="200"></v2-table-column>
                    <v2-table-column label="Country" prop="country" sortable></v2-table-column>
                    <v2-table-column label="Address" prop="street_address" sortable>
                        <template slot-scope="row">
                            <div class="custom-action-row">
                                <el-tooltip class="item" effect="dark" :content="row.street_address" placement="left">
                                    <span>{{ row.street_address }}</span>
                                </el-tooltip>
                            </div>
                        </template>
                    </v2-table-column>
                    <v2-table-column label="Phone" prop="phone" sortable width="150"></v2-table-column>
                    <v2-table-column label="Username" prop="username" sortable width="200"></v2-table-column>
                    <v2-table-column label="Action" width="70" :fixed="isMobile ? '' : 'right'">
                        <template slot-scope="row">
                            <div class="custom-action-row">
                                <el-button @click="print(row)"><i class="mdi mdi-eye"></i></el-button>
                            </div>
                        </template>
                    </v2-table-column> </component
                ><!-- v2-table -->
            </div>
        </div>
    </div>
</template>

<script>
import users from "@/assets/data/USERS_MOCK_DATA.json"
import Papa from "papaparse"
import * as FS from "file-saver"
import _ from "lodash"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "V2TablePage",
    data() {
        return {
            isMobile: false,
            asyncComponent: null,
            width: 0,
            height: "auto",
            currentPage: 1,
            loading: false,
            shownPagination: true,
            showSummary: false,
            search: "",
            paginationInfo: {
                //text: `<span><strong>20</strong> per page</span>`,
                pageSize: 20,
                nextPageText: "›",
                prevPageText: "‹"
            },
            sortingProp: "birth_day",
            sortingOrder: "descending",
            list: users
        }
    },
    computed: {
        listFiltered() {
            return this.list.filter(obj => {
                let ctrl = false
                for (let k in obj) {
                    if (obj[k] && obj[k].toString().toLowerCase().indexOf(this.search.toLowerCase()) !== -1) ctrl = true
                }
                return ctrl
            })
        },
        listSortered() {
            let prop = this.sortingProp
            let order = this.sortingOrder
            return [].concat(
                this.listFiltered.sort((item1, item2) => {
                    let val1 = ""
                    let val2 = ""

                    /*if (prop === 'formatted_date') {
					val1 = parseInt(moment(item1[prop], 'DD/MM/YYYY').format('x'))
					val2 = parseInt(moment(item2[prop], 'DD/MM/YYYY').format('x'))
					if (order === 'descending') {
						return val2 < val1 ? -1 : 1
					}
					return val1 < val2 ? -1 : 1
				}*/

                    val1 = item1[prop]
                    val2 = item2[prop]
                    if (order === "descending") {
                        return val2 < val1 ? -1 : 1
                    }
                    return val1 < val2 ? -1 : 1
                })
            )
        },
        listInPage() {
            let from = (this.currentPage - 1) * this.pageSize
            let to = from + this.pageSize * 1
            return this.listSortered.slice(from, to)
        },
        total() {
            return this.listFiltered.length
        },
        pageSize() {
            return this.paginationInfo.pageSize
        }
    },
    watch: {
        total(val) {
            this.updatePaginationText()
        },
        asyncComponent(val) {
            this.updatePaginationText()
        },
        pageSize(val) {
            this.asyncComponent = null
            this.currentPage = 1

            setTimeout(() => {
                this.asyncComponent = "v2-table"
            }, 500)
        },
        search(val) {
            this.currentPage = 1
        },
        currentPage(val) {
            this.$refs.table.curPage = val
        }
    },
    methods: {
        updatePaginationText() {
            this.paginationInfo.text = `<span>Total of <strong>${this.total}</strong>, <strong>${this.paginationInfo.pageSize}</strong> per page</span>`
        },
        handlePageChange(page) {
            this.currentPage = page
        },
        handleSortChange({ prop, order }) {
            this.sortingProp = prop
            this.sortingOrder = order
        },
        handleSelectChange(rows) {
            console.log("handleSelectChange", rows)
        },
        downloadCSV() {
            var dataCSV = Papa.unparse(this.listFiltered, { header: true })
            const blob = new Blob([dataCSV], { type: "text/csv;charset=utf-8" })
            FS.saveAs(blob, "list.csv")
        },
        print(row) {
            let message = ""

            for (let k in row) {
                message += k + ": <strong>" + row[k] + "</strong><br>"
            }

            this.$alert(message, row.full_name || "Message", {
                dangerouslyUseHTMLString: true
            })
        },
        calcDims() {
            this.width = document.getElementById("table-wrapper").clientWidth

            if (!this.isMobile) {
                this.height = document.getElementById("table-wrapper").clientHeight - 40
                if (this.showSummary) this.height -= 40
                if (this.shownPagination) this.height -= 40
            }

            this.asyncComponent = "v2-table"
        },
        handleResize: _.throttle(function (e) {
            this.asyncComponent = null
            this.width = 0
            this.currentPage = 1
            setTimeout(this.calcDims, 1000)
        }, 500)
    },
    filters: {
        selected: function (value, sel) {
            if (!value) return ""
            if (!sel) return value
            return value.toString().replace(new RegExp(sel, "gim"), `<span class="sel">${sel}</span>`)
        }
    },
    created() {
        if (window.innerWidth <= 768) this.isMobile = true

        this.updatePaginationText()
    },
    mounted() {
        //ie fix
        if (!window.Number.parseInt) window.Number.parseInt = parseInt

        this.calcDims()
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";
.page-table {
    &.overflow {
        overflow: auto;
    }

    .table-box {
        overflow: hidden;
    }
}
</style>
<style lang="scss">
@import "../../../assets/scss/_variables";
.page-table {
    .custom-action-row {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;

        .el-button {
            padding: 1px 5px;
        }
    }

    .toolbar-box {
        .search-box {
            & > div {
                width: 20px;
                display: inline-block;
            }

            margin-bottom: 10px;

            i {
                display: inline-block;
                width: 22px;
            }

            input {
                outline: none;
                background: transparent;
                border: none;
                font-size: 15px;
                position: relative;
                padding: 0;
                margin-left: -20px;
                display: inline-block;
                padding-left: 20px;
                box-sizing: border-box;
                top: -1px;
                width: 100%;
                color: $text-color-primary;
            }

            .icons-tot {
                margin-right: 20px;
            }
        }

        .pagination-box {
            width: 120px;
            margin: 0 15px;

            .select-box {
                width: 70px;
                display: inline-block;
            }

            .label {
                width: 50px;
                display: inline-block;
            }

            .el-input__inner {
                height: 22px;
                border: none;
                background: transparent;
                font-size: 16px;
                text-align: right;
                font-family: inherit;
                padding-right: 20px;
                color: $text-color-primary;
            }

            .el-input__suffix {
                right: -3px;

                .el-select__caret {
                    color: transparentize($text-color-primary, 0.7);
                }
            }
        }

        a,
        button {
            padding: 0;
            margin: 0 15px;
            background: transparent;
            border: none;
            outline: none;
            font-family: inherit;
            font-size: inherit;
            cursor: pointer;

            border-bottom: 1px solid;
            text-decoration: none;
            color: $text-color-primary;
            &:hover {
                opacity: 0.6;
            }
        }

        a {
            margin-right: 0;
        }
    }

    .sel-string {
        .sel {
            background: transparentize($text-color-primary, 0.8);
            border-radius: 5px;
            text-transform: uppercase;
        }
    }
}

@media (max-width: 768px) {
    .page-table {
        .toolbar-box {
            display: block;
            overflow: hidden;
            font-size: 80%;

            & > * {
                display: inline-block;
                min-width: 120px;
                height: 22px;
                background: rgba(0, 0, 0, 0.04);
                padding: 4px;
                margin: 3px !important;
            }
        }
    }
}
</style>
