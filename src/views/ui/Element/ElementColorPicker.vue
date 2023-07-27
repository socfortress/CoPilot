<template>
    <el-scrollbar class="page-element-color-picker">
        <div class="page-header">
            <h1>
                Element Color Picker
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/color-picker" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Alpha" name="1">
                    <el-color-picker v-model="color3" show-alpha></el-color-picker>
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
    name: "ElementColorPicker",
    data() {
        return {
            color3: "rgba(19, 206, 102, 0.8)",
            code1: `
<el-color-picker v-model="color3" show-alpha></el-color-picker>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        color3: 'rgba(19, 206, 102, 0.8)'
      }
    }
  };
<\/script>`
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
