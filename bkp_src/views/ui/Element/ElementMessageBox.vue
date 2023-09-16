<template>
    <div class="page-element-message-box scrollable">
        <div class="page-header">
            <h1>
                Element Message Box
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/message-box" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Use HTML String" name="1">
                    <el-button :link="true" @click="open5">Click to open Message Box</el-button>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Prompt" name="1">
                    <el-button :link="true" @click="open3">Click to open Message Box</el-button>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Centered content" name="1">
                    <el-button :link="true" @click="open6">Click to open Message Box</el-button>
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

import { defineComponent } from "vue"

export default defineComponent({
    name: "ElementMessageBox",
    methods: {
        open5() {
            this.$alert("<strong>This is <i>HTML</i> string</strong>", "HTML String", {
                dangerouslyUseHTMLString: true
            })
        },
        open6() {
            this.$confirm("This will permanently delete the file. Continue?", "Warning", {
                confirmButtonText: "OK",
                cancelButtonText: "Cancel",
                type: "warning",
                center: true
            })
                .then(() => {
                    this.$message({
                        type: "success",
                        showClose: true,
                        message: "Delete completed"
                    })
                })
                .catch(() => {
                    this.$message({
                        type: "info",
                        showClose: true,
                        message: "Delete canceled"
                    })
                })
        },
        open3() {
            this.$prompt("Please input your e-mail", "Tip", {
                confirmButtonText: "OK",
                cancelButtonText: "Cancel",
                inputPattern: /[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?/,
                inputErrorMessage: "Invalid Email"
            })
                .then(value => {
                    this.$message({
                        type: "success",
                        showClose: true,
                        message: "Your email is:" + value
                    })
                })
                .catch(() => {
                    this.$message({
                        type: "info",
                        showClose: true,
                        message: "Input canceled"
                    })
                })
        }
    },
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<template>
  <el-button :link="true" @click="open5">Click to open Message Box</el-button>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    methods: {
      open5() {
        this.$alert('<strong>This is <i>HTML</i> string</strong>', 'HTML String', {
          dangerouslyUseHTMLString: true
        });
      }
    }
  }
<\/script>`,
            code2: `
<template>
  <el-button :link="true" @click="open6">Click to open Message Box</el-button>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    methods: {
      open6() {
        this.$confirm('This will permanently delete the file. Continue?', 'Warning', {
          confirmButtonText: 'OK',
          cancelButtonText: 'Cancel',
          type: 'warning',
          center: true
        }).then(() => {
          this.$message({
            type: 'success',
            message: 'Delete completed'
          });
        }).catch(() => {
          this.$message({
            type: 'info',
            message: 'Delete canceled'
          });
        });
      }
    }
  }
<\/script>
`,
            code3: `
<template>
  <el-button :link="true" @click="open3">Click to open Message Box</el-button>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    methods: {
      open3() {
        this.$prompt('Please input your e-mail', 'Tip', {
          confirmButtonText: 'OK',
          cancelButtonText: 'Cancel',
          inputPattern: /[\w!#$%&'*+/=?^_{|}~-]+(?:\.[\w!#$%&'*+/=?^_{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?/,
          inputErrorMessage: 'Invalid Email'
        }).then(value => {
          this.$message({
            type: 'success',
            message: 'Your email is:' + value
          });
        }).catch(() => {
          this.$message({
            type: 'info',
            message: 'Input canceled'
          });
        });
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
