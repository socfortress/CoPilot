<template>
    <el-scrollbar class="page-element-collapse">
        <div class="page-header">
            <h1>
                Element Collapse
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/collapse" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="block">
                        <el-collapse v-model="activeNames" @change="handleChange">
                            <el-collapse-item title="Consistency" name="1">
                                <div>
                                    Consistent with real life: in line with the process and logic of real life, and comply with languages
                                    and habits that the users are used to;
                                </div>
                                <div>
                                    Consistent within interface: all elements should be consistent, such as: design style, icons and texts,
                                    position of elements, etc.
                                </div>
                            </el-collapse-item>
                            <el-collapse-item title="Feedback" name="2">
                                <div>
                                    Operation feedback: enable the users to clearly perceive their operations by style updates and
                                    interactive effects;
                                </div>
                                <div>Visual feedback: reflect current state by updating or rearranging elements of the page.</div>
                            </el-collapse-item>
                            <el-collapse-item title="Efficiency" name="3">
                                <div>Simplify the process: keep operating process simple and intuitive;</div>
                                <div>
                                    Definite and clear: enunciate your intentions clearly so that the users can quickly understand and make
                                    decisions;
                                </div>
                                <div>
                                    Easy to identify: the interface should be straightforward, which helps the users to identify and frees
                                    them from memorizing and recalling.
                                </div>
                            </el-collapse-item>
                            <el-collapse-item title="Controllability" name="4">
                                <div>
                                    Decision making: giving advices about operations is acceptable, but do not make decisions for the users;
                                </div>
                                <div>
                                    Controlled consequences: users should be granted the freedom to operate, including canceling, aborting
                                    or terminating current operation.
                                </div>
                            </el-collapse-item>
                        </el-collapse>
                    </div>
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
    name: "ElementCollapse",
    methods: {
        handleChange(val) {
            console.log(val)
        }
    },
    data() {
        return {
            activeNames: ["1"],
            code1: `
<el-collapse v-model="activeNames" @change="handleChange">
  <el-collapse-item title="Consistency" name="1">
    <div>Consistent with real life: in line with the process and logic of real life, and comply with languages and habits that the users are used to;</div>
    <div>Consistent within interface: all elements should be consistent, such as: design style, icons and texts, position of elements, etc.</div>
  </el-collapse-item>
  <el-collapse-item title="Feedback" name="2">
    <div>Operation feedback: enable the users to clearly perceive their operations by style updates and interactive effects;</div>
    <div>Visual feedback: reflect current state by updating or rearranging elements of the page.</div>
  </el-collapse-item>
  <el-collapse-item title="Efficiency" name="3">
    <div>Simplify the process: keep operating process simple and intuitive;</div>
    <div>Definite and clear: enunciate your intentions clearly so that the users can quickly understand and make decisions;</div>
    <div>Easy to identify: the interface should be straightforward, which helps the users to identify and frees them from memorizing and recalling.</div>
  </el-collapse-item>
  <el-collapse-item title="Controllability" name="4">
    <div>Decision making: giving advices about operations is acceptable, but do not make decisions for the users;</div>
    <div>Controlled consequences: users should be granted the freedom to operate, including canceling, aborting or terminating current operation.</div>
  </el-collapse-item>
</el-collapse>
<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        activeNames: ['1']
      };
    },
    methods: {
      handleChange(val) {
        console.log(val);
      }
    }
  }
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
.block {
    padding: 20px;
}

@media (max-width: 768px) {
    code {
        font-size: 70%;
    }
}
</style>
