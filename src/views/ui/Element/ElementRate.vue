<template>
    <div class="page-element-rate scrollable">
        <div class="page-header">
            <h1>
                Element Rate
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/rate" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="block">
                        <el-rate
                            v-model="value2"
                            show-text
                            :texts="['oops', 'disappointed', 'normal', 'good', 'great']"
                            :colors="['#99A9BF', '#F7BA2A', '#FF9900']"
                        >
                        </el-rate>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="More icons" name="1">
                    <div class="block">
                        <el-rate
                            v-model="value4"
                            :icon-classes="[
                                'mdi mdi-emoticon-sad',
                                'mdi mdi-emoticon-neutral',
                                'mdi mdi-emoticon-happy'
                            ]"
                            void-icon-class="mdi mdi-emoticon-sad"
                            :colors="['#99A9BF', '#F7BA2A', '#FF9900']"
                        >
                        </el-rate>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </div>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementRate",
    data() {
        return {
            value2: null,
            value4: null,
            code1: `
<el-rate
	v-model="value2"
	show-text
	:texts="['oops', 'disappointed', 'normal', 'good', 'great']"
	:colors="['#99A9BF', '#F7BA2A', '#FF9900']">
</el-rate>`,
            code2: `
<el-rate
	v-model="value4"
	:icon-classes="['mdi mdi-emoticon-sad', 'mdi mdi-emoticon-neutral', 'mdi mdi-emoticon-happy']"
	void-icon-class="mdi mdi-emoticon-sad"
	:colors="['#99A9BF', '#F7BA2A', '#FF9900']">
</el-rate>
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
