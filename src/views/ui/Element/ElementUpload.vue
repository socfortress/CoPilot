<template>
    <el-scrollbar class="page-element-upload">
        <div class="page-header">
            <h1>
                Element Upload
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/upload" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Click to upload files" name="1">
                    <div class="block">
                        <el-upload
                            class="upload-demo"
                            action="https://jsonplaceholder.typicode.com/posts/"
                            :on-preview="handlePreview"
                            :on-remove="handleRemove"
                            :before-remove="beforeRemove"
                            multiple
                            drag
                            :limit="3"
                            :on-exceed="handleExceed"
                            :file-list="fileList"
                        >
                            <i class="el-icon-upload"></i>
                            <div class="el-upload__text">Drop file here or <em>click to upload</em></div>
                            <div class="el-upload__tip" slot="tip">jpg/png files with a size less than 500kb</div>
                        </el-upload>
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
    name: "ElementUpload",
    data() {
        return {
            fileList: [
                {
                    name: "food.jpeg",
                    url: "https://fuss10.elemecdn.com/3/63/4e7f3a15429bfda99bce42a18cdd1jpeg.jpeg?imageMogr2/thumbnail/360x360/format/webp/quality/100"
                },
                {
                    name: "food2.jpeg",
                    url: "https://fuss10.elemecdn.com/3/63/4e7f3a15429bfda99bce42a18cdd1jpeg.jpeg?imageMogr2/thumbnail/360x360/format/webp/quality/100"
                }
            ],
            code1: `
<el-upload
  class="upload-demo"
  action="https://jsonplaceholder.typicode.com/posts/"
  :on-preview="handlePreview"
  :on-remove="handleRemove"
  :before-remove="beforeRemove"
  multiple
  drag
  :limit="3"
  :on-exceed="handleExceed"
  :file-list="fileList">
  <i class="el-icon-upload"></i>
  <div class="el-upload__text">Drop file here or <em>click to upload</em></div>
  <div class="el-upload__tip" slot="tip">jpg/png files with a size less than 500kb</div>
</el-upload>
<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        fileList: [{name: 'food.jpeg', url: 'https://fuss10.elemecdn.com/3/63/4e7f3a15429bfda99bce42a18cdd1jpeg.jpeg?imageMogr2/thumbnail/360x360/format/webp/quality/100'}, {name: 'food2.jpeg', url: 'https://fuss10.elemecdn.com/3/63/4e7f3a15429bfda99bce42a18cdd1jpeg.jpeg?imageMogr2/thumbnail/360x360/format/webp/quality/100'}]
      };
    },
    methods: {
      handleRemove(file, fileList) {
        console.log(file, fileList);
      },
      handlePreview(file) {
        console.log(file);
      },
      handleExceed(files, fileList) {
        this.$message.warning('The limit is 3, you selected'+files.length+' files this time, add up to '+files.length + fileList.length'+ totally');
      },
      beforeRemove(file, fileList) {
        return this.$confirm(file.name+'?');
      }
    }
  }
<\/script>`
        }
    },
    methods: {
        handleRemove(file, fileList) {
            console.log(file, fileList)
        },
        handlePreview(file) {
            console.log(file)
        },
        handleExceed(files, fileList) {
            this.$message.warning(
                `The limit is 3, you selected ${files.length} files this time, add up to ${
                    files.length + fileList.length
                } totally`
            )
        },
        beforeRemove(file, fileList) {
            return this.$confirm(`${file.name}？`)
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
    max-width: 360px;
}

@media (max-width: 768px) {
    code {
        font-size: 70%;
    }
}
</style>
