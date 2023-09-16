<template>
    <el-scrollbar class="page-element-time-picker">
        <div class="page-header">
            <h1>
                Element Time Picker
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/time-picker" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Arbitrary time picker" name="1">
                    <el-time-picker
                        v-model="value2"
                        :picker-options="{
                            selectableRange: '18:30:00 - 20:30:00'
                        }"
                        placeholder="Arbitrary time"
                    >
                    </el-time-picker>
                    &nbsp;
                    <el-time-picker
                        arrow-control
                        v-model="value3"
                        :picker-options="{
                            selectableRange: '18:30:00 - 20:30:00'
                        }"
                        placeholder="Arbitrary time"
                    >
                    </el-time-picker>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Fixed time range" name="1">
                    <el-time-select
                        placeholder="Start time"
                        v-model="startTime"
                        :picker-options="{
                            start: '08:30',
                            step: '00:15',
                            end: '18:30'
                        }"
                    >
                    </el-time-select>
                    &nbsp;
                    <el-time-select
                        placeholder="End time"
                        v-model="endTime"
                        :picker-options="{
                            start: '08:30',
                            step: '00:15',
                            end: '18:30',
                            minTime: startTime
                        }"
                    >
                    </el-time-select>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white hidden-xs-only">
            <el-collapse value="1">
                <el-collapse-item title="Arbitrary time range" name="1">
                    <el-time-picker
                        is-range
                        v-model="value4"
                        range-separator="To"
                        start-placeholder="Start time"
                        end-placeholder="End time"
                    >
                    </el-time-picker>
                    &nbsp;
                    <el-time-picker
                        is-range
                        arrow-control
                        v-model="value5"
                        range-separator="To"
                        start-placeholder="Start time"
                        end-placeholder="End time"
                    >
                    </el-time-picker>
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

import { defineComponent } from "vue"

export default defineComponent({
    name: "ElementTimePicker",
    data() {
        return {
            value2: new Date(2016, 9, 10, 18, 40),
            value3: new Date(2016, 9, 10, 18, 40),
            startTime: "",
            endTime: "",
            value4: [new Date(2016, 9, 10, 8, 40), new Date(2016, 9, 10, 9, 40)],
            value5: [new Date(2016, 9, 10, 8, 40), new Date(2016, 9, 10, 9, 40)],
            code1: `
<template>
  <el-time-picker
    v-model="value2"
    :picker-options="{
      selectableRange: '18:30:00 - 20:30:00'
    }"
    placeholder="Arbitrary time">
  </el-time-picker>
  <el-time-picker
    arrow-control
    v-model="value3"
    :picker-options="{
      selectableRange: '18:30:00 - 20:30:00'
    }"
    placeholder="Arbitrary time">
  </el-time-picker>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value2: new Date(2016, 9, 10, 18, 40),
        value3: new Date(2016, 9, 10, 18, 40)
      };
    }
  }
<\/script>
`,
            code2: `
<template>
  <el-time-select
    placeholder="Start time"
    v-model="startTime"
    :picker-options="{
      start: '08:30',
      step: '00:15',
      end: '18:30'
    }">
  </el-time-select>
  <el-time-select
    placeholder="End time"
    v-model="endTime"
    :picker-options="{
      start: '08:30',
      step: '00:15',
      end: '18:30',
      minTime: startTime
    }">
  </el-time-select>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        startTime: '',
        endTime: ''
      };
    }
  }
<\/script>
`,
            code3: `
<template>
  <el-time-picker
    is-range
    v-model="value4"
    range-separator="To"
    start-placeholder="Start time"
    end-placeholder="End time">
  </el-time-picker>
  <el-time-picker
    is-range
    arrow-control
    v-model="value5"
    range-separator="To"
    start-placeholder="Start time"
    end-placeholder="End time">
  </el-time-picker>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        value4: [new Date(2016, 9, 10, 8, 40), new Date(2016, 9, 10, 9, 40)],
        value5: [new Date(2016, 9, 10, 8, 40), new Date(2016, 9, 10, 9, 40)]
      };
    }
  }
<\/script>
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
