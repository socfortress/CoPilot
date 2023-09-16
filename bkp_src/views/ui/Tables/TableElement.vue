<template>
    <div class="page-table scrollable">
        <div class="page-header">
            <h1>Element UI Table</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Tables</el-breadcrumb-item>
                <el-breadcrumb-item>Element UI Table</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="table-box card-base card-shadow--medium">
            <el-table :data="tableData" style="width: 100%">
                <el-table-column
                    prop="date"
                    label="Date"
                    sortable
                    width="180"
                    :filters="[
                        { text: '2016-05-01', value: '2016-05-01' },
                        { text: '2016-05-02', value: '2016-05-02' },
                        { text: '2016-05-03', value: '2016-05-03' },
                        { text: '2016-05-04', value: '2016-05-04' }
                    ]"
                    :filter-method="filterHandler"
                ></el-table-column>
                <el-table-column prop="name" label="Name" width="180"></el-table-column>
                <el-table-column prop="address" label="Address" :formatter="formatter"></el-table-column>
                <el-table-column
                    prop="tag"
                    label="Tag"
                    width="100"
                    :filters="[
                        { text: 'Home', value: 'Home' },
                        { text: 'Office', value: 'Office' }
                    ]"
                    :filter-method="filterTag"
                    filter-placement="bottom-end"
                >
                    <template v-slot="scope">
                        <el-tag :type="scope.row.tag === 'Home' ? 'primary' : 'success'" close-transition>{{ scope.row.tag }}</el-tag>
                    </template>
                </el-table-column>
            </el-table>
        </div>

        <h4>
            <a href="http://element.eleme.io/#/en-US/component/table" target="_blank"><i class="mdi mdi-link-variant"></i> reference</a>
        </h4>
    </div>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "TableElement",
    data() {
        return {
            tableData: [
                { date: "2016-05-03", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Home" },
                { date: "2016-05-02", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" },
                { date: "2016-05-04", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Home" },
                { date: "2016-05-01", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" },
                { date: "2016-05-01", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" },
                { date: "2016-05-01", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" },
                { date: "2016-05-01", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" },
                { date: "2016-05-01", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" },
                { date: "2016-05-01", name: "Tom", address: "No. 189, Grove St, Los Angeles", tag: "Office" }
            ]
        }
    },
    methods: {
        formatter(row, column) {
            return row.address
        },
        filterTag(value, row) {
            return row.tag === value
        },
        filterHandler(value, row, column) {
            const property = column["property"]
            return row[property] === value
        }
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.table-box {
    overflow: auto;
}
</style>
