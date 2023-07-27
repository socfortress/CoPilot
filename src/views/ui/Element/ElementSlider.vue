<template>
    <div class="page-element-slider scrollable">
        <div class="page-header">
            <h1>
                Element Slider
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/slider" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="block">
                        <span class="demonstration">Default value</span>
                        <el-slider v-model="value1"></el-slider>
                    </div>
                    <div class="block">
                        <span class="demonstration">Customized initial value</span>
                        <el-slider v-model="value2"></el-slider>
                    </div>
                    <div class="block">
                        <span class="demonstration">Hide Tooltip</span>
                        <el-slider v-model="value3" :show-tooltip="false"></el-slider>
                    </div>
                    <div class="block">
                        <span class="demonstration">Format Tooltip</span>
                        <el-slider v-model="value4" :format-tooltip="formatTooltip"></el-slider>
                    </div>
                    <div class="block">
                        <span class="demonstration">Disabled</span>
                        <el-slider v-model="value5" disabled></el-slider>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Discrete values" name="1">
                    <div class="block">
                        <span class="demonstration">Breakpoints not displayed</span>
                        <el-slider v-model="value6" :step="10"> </el-slider>
                    </div>
                    <div class="block">
                        <span class="demonstration">Breakpoints displayed</span>
                        <el-slider v-model="value7" :step="10" show-stops> </el-slider>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Slider with input box" name="1">
                    <div class="block">
                        <el-slider v-model="value8" show-input> </el-slider>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Range selection" name="1">
                    <div class="block">
                        <el-slider v-model="value9" range show-stops :max="10"> </el-slider>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code4"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Vertical mode" name="1">
                    <div class="block">
                        <el-slider v-model="value10" vertical height="200px"> </el-slider>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code5"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </div>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementSlider",
    data() {
        return {
            value1: 0,
            value2: 50,
            value3: 36,
            value4: 48,
            value5: 42,
            value6: 0,
            value7: 0,
            value8: 0,
            value9: [4, 8],
            value10: 0,
            code1: `
<template>
  <div class="block">
    <span class="demonstration">Default value</span>
    <el-slider v-model="value1"></el-slider>
  </div>
  <div class="block">
    <span class="demonstration">Customized initial value</span>
    <el-slider v-model="value2"></el-slider>
  </div>
  <div class="block">
    <span class="demonstration">Hide Tooltip</span>
    <el-slider v-model="value3" :show-tooltip="false"></el-slider>
  </div>
  <div class="block">
    <span class="demonstration">Format Tooltip</span>
    <el-slider v-model="value4" :format-tooltip="formatTooltip"></el-slider>
  </div>
  <div class="block">
    <span class="demonstration">Disabled</span>
    <el-slider v-model="value5" disabled></el-slider>
  </div>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value1: 0,
        value2: 50,
        value3: 36,
        value4: 48,
        value5: 42
      }
    },
    methods: {
      formatTooltip(val) {
        return val / 100;
      }
    }
  }
<\/script>`,
            code2: `
<template>
  <div class="block">
    <span class="demonstration">Breakpoints not displayed</span>
    <el-slider
      v-model="value6"
      :step="10">
    </el-slider>
  </div>
  <div class="block">
    <span class="demonstration">Breakpoints displayed</span>
    <el-slider
      v-model="value7"
      :step="10"
      show-stops>
    </el-slider>
  </div>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value6: 0,
        value7: 0
      }
    }
  }
<\/script>
`,
            code3: `
<template>
  <div class="block">
    <el-slider
      v-model="value8"
      show-input>
    </el-slider>
  </div>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value8: 0
      }
    }
  }
<\/script>
`,
            code4: `
<template>
  <div class="block">
    <el-slider
      v-model="value9"
      range
      show-stops
      :max="10">
    </el-slider>
  </div>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value9: [4, 8]
      }
    }
  }
<\/script>
`,
            code5: `
<template>
  <div class="block">
    <el-slider
      v-model="value10"
      vertical
      height="200px">
    </el-slider>
  </div>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value10: 0
      }
    }
  }
<\/script>
`
        }
    },
    methods: {
        formatTooltip(val) {
            return val / 100
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
    padding: 15px;
}

@media (max-width: 768px) {
    code {
        font-size: 70%;
    }
}
</style>
