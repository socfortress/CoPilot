<template>
    <el-scrollbar class="page-element-tooltip">
        <div class="page-header">
            <h1>
                Element Tooltip
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/tooltip" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white hidden-xs-only">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="box">
                        <div class="top">
                            <el-tooltip class="item" effect="dark" content="Top Left prompts info" placement="top-start">
                                <el-button>top-start</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Top Center prompts info" placement="top">
                                <el-button>top</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Top Right prompts info" placement="top-end">
                                <el-button>top-end</el-button>
                            </el-tooltip>
                        </div>
                        <div class="left">
                            <el-tooltip class="item" effect="dark" content="Left Top prompts info" placement="left-start">
                                <el-button>left-start</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Left Center prompts info" placement="left">
                                <el-button>left</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Left Bottom prompts info" placement="left-end">
                                <el-button>left-end</el-button>
                            </el-tooltip>
                        </div>

                        <div class="right">
                            <el-tooltip class="item" effect="dark" content="Right Top prompts info" placement="right-start">
                                <el-button>right-start</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Right Center prompts info" placement="right">
                                <el-button>right</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Right Bottom prompts info" placement="right-end">
                                <el-button>right-end</el-button>
                            </el-tooltip>
                        </div>
                        <div class="bottom">
                            <el-tooltip class="item" effect="dark" content="Bottom Left prompts info" placement="bottom-start">
                                <el-button>bottom-start</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Bottom Center prompts info" placement="bottom">
                                <el-button>bottom</el-button>
                            </el-tooltip>
                            <el-tooltip class="item" effect="dark" content="Bottom Right prompts info" placement="bottom-end">
                                <el-button>bottom-end</el-button>
                            </el-tooltip>
                        </div>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Theme" name="1">
                    <el-tooltip content="Top center" placement="top">
                        <el-button>Dark</el-button>
                    </el-tooltip>
                    <el-tooltip content="Bottom center" placement="bottom" effect="light">
                        <el-button>Light</el-button>
                    </el-tooltip>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="More Content" name="1">
                    <el-tooltip placement="top">
                        <div slot="content">multiple lines<br />second line</div>
                        <el-button>Top center</el-button>
                    </el-tooltip>
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
    name: "ElementTooltip",
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<div class="box">
  <div class="top">
    <el-tooltip class="item" effect="dark" content="Top Left prompts info" placement="top-start">
      <el-button>top-start</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Top Center prompts info" placement="top">
      <el-button>top</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Top Right prompts info" placement="top-end">
      <el-button>top-end</el-button>
    </el-tooltip>
  </div>
  <div class="left">
    <el-tooltip class="item" effect="dark" content="Left Top prompts info" placement="left-start">
      <el-button>left-start</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Left Center prompts info" placement="left">
      <el-button>left</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Left Bottom prompts info" placement="left-end">
      <el-button>left-end</el-button>
    </el-tooltip>
  </div>

  <div class="right">
    <el-tooltip class="item" effect="dark" content="Right Top prompts info" placement="right-start">
      <el-button>right-start</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Right Center prompts info" placement="right">
      <el-button>right</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Right Bottom prompts info" placement="right-end">
      <el-button>right-end</el-button>
    </el-tooltip>
  </div>
  <div class="bottom">
    <el-tooltip class="item" effect="dark" content="Bottom Left prompts info" placement="bottom-start">
      <el-button>bottom-start</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Bottom Center prompts info" placement="bottom">
      <el-button>bottom</el-button>
    </el-tooltip>
    <el-tooltip class="item" effect="dark" content="Bottom Right prompts info" placement="bottom-end">
      <el-button>bottom-end</el-button>
    </el-tooltip>
  </div>
</div>

<style>
  .box {
    width: 400px;

    .top {
      text-align: center;
    }

    .left {
      float: left;
      width: 110px;
    }

    .right {
      float: right;
      width: 110px;
    }

    .bottom {
      clear: both;
      text-align: center;
    }

    .item {
      margin: 4px;
    }

    .left .el-tooltip__popper,
    .right .el-tooltip__popper {
      padding: 8px 10px;
    }

    .el-button {
      width: 110px;
    }
  }
</style>`,
            code2: `
<el-tooltip content="Top center" placement="top">
  <el-button>Dark</el-button>
</el-tooltip>
<el-tooltip content="Bottom center" placement="bottom" effect="light">
  <el-button>Light</el-button>
</el-tooltip>
`,
            code3: `
<el-tooltip placement="top">
  <div slot="content">multiple lines<br/>second line</div>
  <el-button>Top center</el-button>
</el-tooltip>
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

.box {
    width: 400px;

    .top {
        text-align: center;
    }

    .left {
        float: left;
        width: 110px;
    }

    .right {
        float: right;
        width: 110px;
    }

    .bottom {
        clear: both;
        text-align: center;
    }

    .item {
        margin: 4px;
    }

    .left .el-tooltip__popper,
    .right .el-tooltip__popper {
        padding: 8px 10px;
    }

    .el-button {
        width: 110px;
    }
}
</style>
