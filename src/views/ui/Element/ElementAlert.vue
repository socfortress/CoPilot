<template>
    <el-scrollbar class="page-element-alert">
        <div class="page-header">
            <h1>
                Element Alert
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/alert" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="With icon and description" name="1">
                    <el-alert title="success alert" type="success" description="more text description" show-icon>
                    </el-alert>
                    &nbsp;
                    <el-alert title="info alert" type="info" description="more text description" show-icon> </el-alert>
                    &nbsp;
                    <el-alert title="warning alert" type="warning" description="more text description" show-icon>
                    </el-alert>
                    &nbsp;
                    <el-alert title="error alert" type="error" description="more text description" show-icon>
                    </el-alert>
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

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementAlert",
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<el-alert
	title="success alert"
	type="success"
	description="more text description"
	show-icon>
</el-alert>
<el-alert
	title="info alert"
	type="info"
	description="more text description"
	show-icon>
</el-alert>
<el-alert
	title="warning alert"
	type="warning"
	description="more text description"
	show-icon>
</el-alert>
<el-alert
	title="error alert"
	type="error"
	description="more text description"
	show-icon>
</el-alert>`
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
