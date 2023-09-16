<template>
    <el-scrollbar class="page-page-headers">
        <div class="page-header">
            <h1>Basic header</h1>
            <h4>sub header</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Basic header</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="page-header card-base">
            <h1>Card header</h1>
            <h4>sub header</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Card header</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="page-header card-base card-shadow--small">
            <h1>Card shadow header</h1>
            <h4>sub header</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Card shadow header</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="page-header header-accent-gradient card-base card-shadow--small">
            <h1>Gradient header</h1>
            <h4>sub header</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Gradient header</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="page-header header-accent card-base card-shadow--small">
            <h1>Accent header</h1>
            <h4>sub header</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Accent header</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="page-header header-primary card-base card-shadow--small">
            <h1>Primary header</h1>
            <h4>sub header</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Layout</el-breadcrumb-item>
                <el-breadcrumb-item>Primary header</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "PageHeaders"
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-page-headers {
    .page-header {
        margin-bottom: 50px;
    }
}
</style>
