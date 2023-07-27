<template>
    <div class="page-vue-good-table scrollable only-y">
        <div class="page-header">
            <h1>Vue Good Table</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Tables</el-breadcrumb-item>
                <el-breadcrumb-item>Vue good table</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="vue-good-table-box card-base card-shadow--medium">
            <vue-good-table
                :columns="columns"
                :rows="rows"
                :search-options="{
                    enabled: true,
                    placeholder: 'Search this table'
                }"
                :pagination-options="{
                    enabled: true,
                    mode: 'records',
                    perPage: 10,
                    perPageDropdown: [10, 20, 30, 40, 50],
                    nextLabel: 'Next',
                    prevLabel: 'Prev',
                    rowsPerPageLabel: 'Rows per page',
                    ofLabel: 'of',
                    pageLabel: 'page', // for 'pages' mode
                    allLabel: 'All'
                }"
                :lineNumbers="false"
                class="styled"
            >
            </vue-good-table>
        </div>

        <h4>
            <a href="https://github.com/xaksis/vue-good-table" target="_blank"
                ><i class="mdi mdi-link-variant"></i> reference</a
            >
        </h4>
    </div>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "VGTable",
    data() {
        return {
            columns: [
                {
                    label: "Name",
                    field: "name",
                    filterable: true
                },
                {
                    label: "Age",
                    field: "age",
                    type: "number",
                    html: false,
                    filterable: true
                },
                {
                    label: "Created On",
                    field: "createdAt",
                    type: "date",
                    dateInputFormat: "YYYY-MM-DD",
                    dateOutputFormat: "MMM Do YY"
                },
                {
                    label: "Percent",
                    field: "score",
                    type: "percentage",
                    html: false
                }
            ],
            rows: [
                { id: 1, name: "John", age: 20, createdAt: "2010-10-31", score: 0.03343 },
                { id: 2, name: "Jane", age: 24, createdAt: "2011-10-31", score: 0.03343 },
                { id: 3, name: "Susan", age: 16, createdAt: "2011-10-30", score: 0.03343 },
                { id: 4, name: "Chris", age: 55, createdAt: "2011-10-11", score: 0.03343 },
                { id: 5, name: "Dan", age: 40, createdAt: "2011-10-21", score: 0.03343 },
                { id: 6, name: "John", age: 20, createdAt: "2011-10-31", score: 0.03343 },
                { id: 7, name: "Jane", age: 24, createdAt: "20111031" },
                { id: 8, name: "Susan", age: 16, createdAt: "2013-10-31", score: 0.03343 },
                { id: 9, name: "Chris", age: 55, createdAt: "2012-10-31", score: 0.03343 },
                { id: 10, name: "Dan", age: 40, createdAt: "2011-10-31", score: 0.03343 },
                { id: 11, name: "John", age: 20, createdAt: "2011-10-31", score: 0.03343 },
                { id: 12, name: "Jane", age: 24, createdAt: "2011-07-31", score: 0.03343 },
                { id: 13, name: "Susan", age: 16, createdAt: "2017-02-28", score: 0.03343 },
                { id: 14, name: "Chris", age: 55, createdAt: "", score: 0.03343 },
                { id: 15, name: "Dan", age: 40, createdAt: "2011-10-31", score: 0.03343 },
                { id: 19, name: "Chris", age: 55, createdAt: "2011-10-31", score: 0.03343 },
                { id: 20, name: "Dan", age: 40, createdAt: "2011-10-31", score: 0.03343 }
            ]
        }
    }
})
</script>

<style lang="scss">
.page-vue-good-table {
    overflow: hidden;
}
</style>
