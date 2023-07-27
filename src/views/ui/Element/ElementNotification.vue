<template>
    <el-scrollbar class="page-element-notification">
        <div class="page-header">
            <h1>
                Element Notification
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/notification" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="With types" name="1">
                    <el-button class="m-5" plain @click="open3"> Success </el-button>
                    <el-button class="m-5" plain @click="open4"> Warning </el-button>
                    <el-button class="m-5" plain @click="open5"> Info </el-button>
                    <el-button class="m-5" plain @click="open6"> Error </el-button>
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
    name: "ElementNotification",
    methods: {
        open3() {
            this.$notify({
                title: "Success",
                message: "This is a success message",
                type: "success"
            })
        },

        open4() {
            this.$notify({
                title: "Warning",
                message: "This is a warning message",
                type: "warning",
                position: "bottom-right"
            })
        },

        open5() {
            this.$notify.info({
                title: "Info",
                message: "This is an info message",
                position: "bottom-left"
            })
        },

        open6() {
            this.$notify.error({
                title: "Error",
                message: "This is an error message",
                position: "top-left"
            })
        }
    },
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<template>
  <el-button
    plain
    @click="open3">
    Success
  </el-button>
  <el-button
    plain
    @click="open4">
    Warning
  </el-button>
  <el-button
    plain
    @click="open5">
    Info
  </el-button>
  <el-button
    plain
    @click="open6">
    Error
  </el-button>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    methods: {
      open3() {
        this.$notify({
		title: 'Success',
		message: 'This is a success message',
		type: 'success'
        });
      },

      open4() {
        this.$notify({
		title: 'Warning',
		message: 'This is a warning message',
		type: 'warning',
		position: 'bottom-right'
        });
      },

      open5() {
        this.$notify.info({
		title: 'Info',
		message: 'This is an info message',
		position: 'bottom-left'
        });
      },

      open6() {
        this.$notify.error({
		title: 'Error',
		message: 'This is an error message',
		position: 'top-left'
        });
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

@media (max-width: 768px) {
    code {
        font-size: 70%;
    }
}
</style>
