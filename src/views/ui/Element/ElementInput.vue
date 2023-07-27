<template>
    <el-scrollbar class="page-element-input">
        <div class="page-header">
            <h1>
                Element Input
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/input" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <el-input placeholder="Please input" v-model="input"></el-input>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Clearable" name="1">
                    <el-input placeholder="Please input" v-model="input10" clearable> </el-input>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Autosize Textarea" name="1">
                    <el-input type="textarea" autosize placeholder="Please input" v-model="textarea2"> </el-input>
                    <div style="margin: 20px 0"></div>
                    <el-input type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="Please input" v-model="textarea3">
                    </el-input>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Mixed input" name="1">
                    <div>
                        <el-input placeholder="Please input" v-model="input3">
                            <template slot="prepend">Http://</template>
                        </el-input>
                    </div>
                    <div style="margin-top: 15px">
                        <el-input placeholder="Please input" v-model="input4">
                            <template slot="append">.com</template>
                        </el-input>
                    </div>
                    <div style="margin-top: 15px">
                        <el-input placeholder="Please input" v-model="input5" class="input-with-select">
                            <el-select v-model="select" slot="prepend" placeholder="Select">
                                <el-option label="Restaurant" value="1"></el-option>
                                <el-option label="Order No." value="2"></el-option>
                                <el-option label="Tel" value="3"></el-option>
                            </el-select>
                            <el-button slot="append" icon="el-icon-search"></el-button>
                        </el-input>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code4"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </el-scrollbar>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementInput",
    data() {
        return {
            input: "",
            input3: "",
            input4: "",
            input5: "",
            input10: "",
            textarea2: "",
            textarea3: "",
            select: "",
            code1: `
<el-input placeholder="Please input" v-model="input"></el-input>
`,
            code2: `
<el-input
  placeholder="Please input"
  v-model="input10"
  clearable>
</el-input>
`,
            code3: `
<el-input
  type="textarea"
  autosize
  placeholder="Please input"
  v-model="textarea2">
</el-input>
<div style="margin: 20px 0;"></div>
<el-input
  type="textarea"
  :autosize="{ minRows: 2, maxRows: 4}"
  placeholder="Please input"
  v-model="textarea3">
</el-input>
`,
            code4: `
<div>
  <el-input placeholder="Please input" v-model="input3">
    <template slot="prepend">Http://</template>
  </el-input>
</div>
<div style="margin-top: 15px;">
  <el-input placeholder="Please input" v-model="input4">
    <template slot="append">.com</template>
  </el-input>
</div>
<div style="margin-top: 15px;">
  <el-input placeholder="Please input" v-model="input5" class="input-with-select">
    <el-select v-model="select" slot="prepend" placeholder="Select">
      <el-option label="Restaurant" value="1"></el-option>
      <el-option label="Order No." value="2"></el-option>
      <el-option label="Tel" value="3"></el-option>
    </el-select>
    <el-button slot="append" icon="el-icon-search"></el-button>
  </el-input>
</div>

<style>
  .el-select .el-input {
    width: 110px;
  }
  .input-with-select .el-input-group__prepend {
    background-color: #fff;
  }
</style>
<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
  data() {
    return {
      input3: '',
      input4: '',
      input5: '',
      select: ''
    }
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

<style lang="scss">
.demo-box {
    .el-select .el-input {
        min-width: 110px;
    }
}
</style>
