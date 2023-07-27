<template>
    <el-scrollbar class="page-element-steps">
        <div class="page-header">
            <h1>
                Element Steps
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/steps" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <el-steps :active="active" finish-status="success">
                        <el-step title="Step 1"></el-step>
                        <el-step title="Step 2"></el-step>
                        <el-step title="Step 3"></el-step>
                    </el-steps>

                    <el-button style="margin-top: 12px" @click="next">Next step</el-button>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Center" name="1">
                    <el-steps :active="2" align-center>
                        <el-step title="Step 1" description="Some description"></el-step>
                        <el-step title="Step 2" description="Some description"></el-step>
                        <el-step title="Step 3" description="Some description"></el-step>
                        <el-step title="Step 4" description="Some description"></el-step>
                    </el-steps>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Step bar with icon" name="1">
                    <el-steps :active="1">
                        <el-step title="Step 1" icon="el-icon-edit"></el-step>
                        <el-step title="Step 2" icon="el-icon-upload"></el-step>
                        <el-step title="Step 3" icon="el-icon-picture"></el-step>
                    </el-steps>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Vertical step bar" name="1">
                    <div style="height: 300px">
                        <el-steps direction="vertical" :active="1">
                            <el-step title="Step 1"></el-step>
                            <el-step title="Step 2"></el-step>
                            <el-step title="Step 3"></el-step>
                        </el-steps>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code4"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white hidden-xs-only">
            <el-collapse value="1">
                <el-collapse-item title="Simple step bar" name="1">
                    <el-steps :space="200" :active="1" simple>
                        <el-step title="Step 1" icon="el-icon-edit"></el-step>
                        <el-step title="Step 2" icon="el-icon-upload"></el-step>
                        <el-step title="Step 3" icon="el-icon-picture"></el-step>
                    </el-steps>

                    <el-steps :active="1" finish-status="success" simple style="margin-top: 20px">
                        <el-step title="Step 1"></el-step>
                        <el-step title="Step 2"></el-step>
                        <el-step title="Step 3"></el-step>
                    </el-steps>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code5"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </el-scrollbar>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementSteps",
    methods: {
        next() {
            if (this.active++ > 2) this.active = 0
        }
    },
    data() {
        return {
            active: 0,
            code1: `
<el-steps :active="active" finish-status="success">
  <el-step title="Step 1"></el-step>
  <el-step title="Step 2"></el-step>
  <el-step title="Step 3"></el-step>
</el-steps>

<el-button style="margin-top: 12px;" @click="next">Next step</el-button>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        active: 0
      };
    },

    methods: {
      next() {
        if (this.active++ > 2) this.active = 0;
      }
    }
  }
<\/script>`,
            code2: `
<el-steps :active="2" align-center>
  <el-step title="Step 1" description="Some description"></el-step>
  <el-step title="Step 2" description="Some description"></el-step>
  <el-step title="Step 3" description="Some description"></el-step>
  <el-step title="Step 4" description="Some description"></el-step>
</el-steps>
`,
            code3: `
<el-steps :active="1">
  <el-step title="Step 1" icon="el-icon-edit"></el-step>
  <el-step title="Step 2" icon="el-icon-upload"></el-step>
  <el-step title="Step 3" icon="el-icon-picture"></el-step>
</el-steps>
`,
            code4: `
<div style="height: 300px;">
  <el-steps direction="vertical" :active="1">
    <el-step title="Step 1"></el-step>
    <el-step title="Step 2"></el-step>
    <el-step title="Step 3"></el-step>
  </el-steps>
</div>
`,
            code5: `
<el-steps :space="200" :active="1" simple>
  <el-step title="Step 1" icon="el-icon-edit"></el-step>
  <el-step title="Step 2" icon="el-icon-upload"></el-step>
  <el-step title="Step 3" icon="el-icon-picture"></el-step>
</el-steps>

<el-steps :active="1" finish-status="success" simple style="margin-top: 20px">
  <el-step title="Step 1" ></el-step>
  <el-step title="Step 2" ></el-step>
  <el-step title="Step 3" ></el-step>
</el-steps>
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
