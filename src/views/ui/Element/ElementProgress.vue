<template>
    <el-scrollbar class="page-element-progress">
        <div class="page-header">
            <h1>
                Element Progress
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/progress" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Linear progress bar (external percentage)" name="1">
                    <el-progress :percentage="0"></el-progress>
                    &nbsp;
                    <el-progress :percentage="70"></el-progress>
                    &nbsp;
                    <el-progress :percentage="100" status="success"></el-progress>
                    &nbsp;
                    <el-progress :percentage="50" status="exception"></el-progress>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Linear progress bar (internal percentage)" name="1">
                    <el-progress :text-inside="true" :stroke-width="18" :percentage="0"></el-progress>
                    &nbsp;
                    <el-progress :text-inside="true" :stroke-width="18" :percentage="70"></el-progress>
                    &nbsp;
                    <el-progress
                        :text-inside="true"
                        :stroke-width="18"
                        :percentage="100"
                        status="success"
                    ></el-progress>
                    &nbsp;
                    <el-progress
                        :text-inside="true"
                        :stroke-width="18"
                        :percentage="50"
                        status="exception"
                    ></el-progress>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Circular progress bar" name="1">
                    <el-progress type="circle" :percentage="0"></el-progress>
                    &nbsp;
                    <el-progress type="circle" :percentage="25"></el-progress>
                    &nbsp;
                    <el-progress type="circle" :percentage="100" status="success"></el-progress>
                    &nbsp;
                    <el-progress type="circle" :percentage="50" status="exception"></el-progress>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </el-scrollbar>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementProgress",
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<el-progress :percentage="0"></el-progress>
<el-progress :percentage="70"></el-progress>
<el-progress :percentage="100" status="success"></el-progress>
<el-progress :percentage="50" status="exception"></el-progress>
`,
            code2: `
<el-progress :text-inside="true" :stroke-width="18" :percentage="0"></el-progress>
<el-progress :text-inside="true" :stroke-width="18" :percentage="70"></el-progress>
<el-progress :text-inside="true" :stroke-width="18" :percentage="100" status="success"></el-progress>
<el-progress :text-inside="true" :stroke-width="18" :percentage="50" status="exception"></el-progress>
`,
            code3: `
<el-progress type="circle" :percentage="0"></el-progress>
<el-progress type="circle" :percentage="25"></el-progress>
<el-progress type="circle" :percentage="100" status="success"></el-progress>
<el-progress type="circle" :percentage="50" status="exception"></el-progress>
`
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
