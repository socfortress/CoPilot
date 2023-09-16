<template>
    <div class="page-tui-grid flex column">
        <div class="page-header card-base header-accent">
            <h1>TUI Grid</h1>
            <h4>
                <a href="http://ui.toast.com/tui-grid/" target="_blank" class="white-text" style="text-decoration-color: white"
                    >TOAST UI Grid</a
                >
                is a powerful widget which allows you to visualize and edit data via its table representation
                <br />
                Vue 3 compatibility provided by
                <a
                    href="https://www.npmjs.com/package/vue3-tui-grid"
                    target="_blank"
                    class="white-text"
                    style="text-decoration-color: white"
                    >vue3-tui-grid</a
                >
            </h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Tables</el-breadcrumb-item>
                <el-breadcrumb-item>TUI Grid</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <resize-observer @notify="handleResize" />

        <div id="table-box" class="bg-white card-shadow--small b-rad-4 box grow" v-loading="resizing">
            <grid
                id="grid"
                :data="gridProps.data"
                :columns="gridProps.columns"
                :bodyHeight="gridProps.bodyHeight"
                :frozenCount="gridProps.frozenCount"
                :virtualScrolling="gridProps.virtualScrolling"
                :minRowHeight="gridProps.minRowHeight"
                :pagination="gridProps.pagination"
                :rowHeaders="gridProps.rowHeaders"
                :header="gridProps.header"
                :columnOptions="gridProps.columnOptions"
                :summary="gridProps.summary"
                v-if="!resizing"
            />
        </div>
    </div>
</template>

<script>
import "tui-grid/dist/tui-grid.css"
import { TuiGrid as Grid } from "vue3-tui-grid"
import ResizeObserver from "@/components/vue-resize/ResizeObserver.vue"
import _ from "lodash"
import Chance from "chance"
const chance = new Chance()

export default {
    name: "TuiGrid",
    data() {
        const gridData = []

        _.times(500, number => {
            gridData.push({
                name: chance.name(),
                photo: "/static/images/users/user-" + chance.integer({ min: 0, max: 30 }) + ".jpg",
                age: chance.age(),
                gender: chance.gender(),
                city: chance.city(),
                email: chance.email(),
                guid: chance.guid(),
                phone: chance.phone(),
                company: chance.company(),
                profession: chance.profession(),
                id: number
            })
        })

        return {
            grid: null,
            gridData,
            resizing: true,
            height: 300,
            gridProps: {
                bodyHeight: null,
                frozenCount: window.innerWidth <= 768 ? 0 : 2,
                virtualScrolling: true,
                minRowHeight: 60,
                pagination: false,
                rowHeaders: ["checkbox", "rowNum"],
                header: {},
                columnOptions: {
                    //minWidth: 100,
                    frozenCount: window.innerWidth <= 768 ? 0 : 2
                },
                columns: [
                    {
                        header: "",
                        name: "photo",
                        align: "center",
                        width: 40,
                        formatter: function (data) {
                            var url = data.value.toString()
                            return '<img src="' + url + '" width="40" height="40" />'
                        }
                    },
                    {
                        header: "Name",
                        name: "name",
                        minWidth: 200,
                        sortable: true,
                        editOptions: {
                            type: "text",
                            useViewMode: true
                        }
                    },
                    {
                        header: "Age",
                        name: "age",
                        sortable: true,
                        width: 180
                    },
                    {
                        header: "Gender",
                        name: "gender",
                        minWidth: 100,
                        sortable: true,
                        editOptions: {
                            type: "select",
                            listItems: [
                                { text: "Female", value: "Female" },
                                { text: "Male", value: "Male" }
                            ],
                            useViewMode: true
                        }
                    },
                    {
                        header: "City",
                        name: "city",
                        sortable: true,
                        minWidth: 200,
                        editOptions: {
                            type: "text",
                            //maxLength: 10,
                            useViewMode: false
                        }
                    },
                    {
                        header: "Email",
                        name: "email",
                        minWidth: 200,
                        formatter: function (data) {
                            return '<a href="mailto:' + data.value.toString() + '" target="_blank">' + data.value.toString() + "</a>"
                        }
                    },
                    {
                        header: "Phone",
                        name: "phone",
                        minWidth: 200
                    },
                    {
                        header: "Company",
                        name: "company",
                        minWidth: 300
                    },
                    {
                        header: "Profession",
                        name: "profession",
                        minWidth: 300
                    },
                    {
                        header: "GUID",
                        name: "guid",
                        minWidth: 300
                    }
                ],
                summary: {
                    height: 30,
                    position: "bottom", // or 'top'
                    columnContent: {
                        age: {
                            template: function (valueMap) {
                                return (
                                    "<small>MAX: <strong>" +
                                    valueMap.max +
                                    "</strong>, MIN: <strong>" +
                                    valueMap.min +
                                    "</strong>, AVG: <strong>" +
                                    valueMap.avg.toFixed(2) +
                                    "</strong></small>"
                                )
                            }
                        }
                    }
                },
                data: gridData
            }
        }
    },
    methods: {
        handleResize: _.throttle(function (e) {
            console.log("resize", this.resizing)
            if (!this.resizing) {
                this.resizing = true
                setTimeout(() => {
                    this.resizing = false
                }, 1000)
                setTimeout(() => {
                    this.initGrid()
                }, 1500)
            }
        }, 1000),
        initGrid() {
            const tableBox = document.getElementById("table-box")
            if (tableBox) this.gridProps.bodyHeight = tableBox.clientHeight - 71

            this.gridProps.frozenCount = window.innerWidth <= 768 ? 0 : 2
            this.gridProps.columnOptions.frozenCount = window.innerWidth <= 768 ? 0 : 2
        }
    },
    mounted() {
        setTimeout(() => {
            this.initGrid()
        }, 1000)
        setTimeout(() => {
            this.resizing = false
        }, 1500)
    },
    components: {
        Grid,
        ResizeObserver
    }
}
</script>

<style lang="scss">
@import "../../../assets/scss/_variables";

.page-tui-grid {
    .page-header {
        margin-bottom: 20px;
    }

    #table-box {
        overflow: hidden;
    }

    #grid {
        .tui-grid-cell[data-column-name="photo"] {
            .tui-grid-cell-content {
                padding: 0;
            }
        }

        .tui-grid-border-line-top {
            background-color: transparent;
            border-color: white;
        }
        .tui-grid-cell-head {
            border-top-color: transparent;
        }
    }
}
</style>
