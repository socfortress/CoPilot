<template>
    <el-scrollbar class="page-element-breadcrumb">
        <div class="page-header">
            <h1>
                Element Breadcrumb
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/breadcrumb" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <el-breadcrumb separator="/">
                        <el-breadcrumb-item :to="{ path: '/' }">homepage</el-breadcrumb-item>
                        <el-breadcrumb-item>promotion management</el-breadcrumb-item>
                        <el-breadcrumb-item>promotion list</el-breadcrumb-item>
                        <el-breadcrumb-item>promotion detail</el-breadcrumb-item>
                    </el-breadcrumb>
                    &nbsp;
                    <el-breadcrumb separator-class="el-icon-arrow-right">
                        <el-breadcrumb-item :to="{ path: '/' }">homepage</el-breadcrumb-item>
                        <el-breadcrumb-item>promotion management</el-breadcrumb-item>
                        <el-breadcrumb-item>promotion list</el-breadcrumb-item>
                        <el-breadcrumb-item>promotion detail</el-breadcrumb-item>
                    </el-breadcrumb>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </el-scrollbar>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "vue"

export default defineComponent({
    name: "ElementBreadcrumb",
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<el-breadcrumb separator="/">
  <el-breadcrumb-item :to="{ path: '/' }">homepage</el-breadcrumb-item>
  <el-breadcrumb-item>promotion management</el-breadcrumb-item>
  <el-breadcrumb-item>promotion list</el-breadcrumb-item>
  <el-breadcrumb-item>promotion detail</el-breadcrumb-item>
</el-breadcrumb>
<el-breadcrumb separator-class="el-icon-arrow-right">
  <el-breadcrumb-item :to="{ path: '/' }">homepage</el-breadcrumb-item>
  <el-breadcrumb-item>promotion management</el-breadcrumb-item>
  <el-breadcrumb-item>promotion list</el-breadcrumb-item>
  <el-breadcrumb-item>promotion detail</el-breadcrumb-item>
</el-breadcrumb>`
        }
    },
    components: {
        ThemePicker
    }
})
</script>

<style lang="scss" scoped>
.demo-box {
    padding: 20px;
    margin-bottom: 20px;
}
pre {
    margin: 0;
    background: white;
}
code {
    padding: 0;
}

@media (max-width: 768px) {
    code {
        font-size: 70%;
    }
}
</style>
