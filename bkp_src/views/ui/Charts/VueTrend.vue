<template>
    <div class="page-vuetrend scrollable">
        <div class="page-header">
            <h1>Vue Trend</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Components</el-breadcrumb-item>
                <el-breadcrumb-item>Charts</el-breadcrumb-item>
                <el-breadcrumb-item>Vue Trend</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium p-10">
            <trend :data="data" :gradient="['#6fa8dc', '#42b983', '#2c3e50']" auto-draw smooth></trend>
        </div>

        <h4>
            <a href="https://github.com/QingWei-Li/vue-trend" target="_blank"><i class="mdi mdi-link-variant"></i>reference</a>
        </h4>
    </div>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "VueTrendPage",
    data() {
        return {
            data: [5, 3, 9, 6, 5, 9, 7, 3, 5, 2, 5, 3, 9, 6, 5, 9, 7, 3, 5, 2]
        }
    },
    created() {
        setTimeout(() => {
            setInterval(() => {
                let random = Math.round(Math.random() * 10)
                this.data.shift()
                this.data.push(random)
            }, 2000)
        }, 1000)
    }
})
</script>

<style lang="scss"></style>
