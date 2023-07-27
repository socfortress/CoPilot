<template>
    <el-scrollbar class="page-element-message">
        <div class="page-header">
            <h1>
                Element Message
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/message" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Closable" name="1">
                    <el-button :plain="true" @click="open5" class="m-5">message</el-button>
                    <el-button :plain="true" @click="open6" class="m-5">success</el-button>
                    <el-button :plain="true" @click="open7" class="m-5">warning</el-button>
                    <el-button :plain="true" @click="open8" class="m-5">error</el-button>
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
    name: "ElementMessage",
    methods: {
        open5() {
            this.$message({
                showClose: true,
                message: "This is a message."
            })
        },

        open6() {
            this.$message({
                showClose: true,
                message: "Congrats, this is a success message.",
                type: "success"
            })
        },

        open7() {
            this.$message({
                showClose: true,
                message: "Warning, this is a warning message.",
                type: "warning"
            })
        },

        open8() {
            this.$message({
                showClose: true,
                message: "Oops, this is a error message.",
                type: "error"
            })
        }
    },
    data() {
        return {
            code1: `
<template>
  <el-button :plain="true" @click="open5">message</el-button>
  <el-button :plain="true" @click="open6">success</el-button>
  <el-button :plain="true" @click="open7">warning</el-button>
  <el-button :plain="true" @click="open8">error</el-button>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    methods: {
      open5() {
        this.$message({
          showClose: true,
          message: 'This is a message.'
        });
      },

      open6() {
        this.$message({
          showClose: true,
          message: 'Congrats, this is a success message.',
          type: 'success'
        });
      },

      open7() {
        this.$message({
          showClose: true,
          message: 'Warning, this is a warning message.',
          type: 'warning'
        });
      },

      open8() {
        this.$message({
          showClose: true,
          message: 'Oops, this is a error message.',
          type: 'error'
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
