<template>
    <el-scrollbar class="page-element-card">
        <div class="page-header">
            <h1>
                Element Card
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/card" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="block">
                        <el-card class="box-card">
                            <div slot="header" class="clearfix">
                                <span>Card name</span>
                                <el-button style="float: right; padding: 3px 0" :link="true">Operation button</el-button>
                            </div>
                            <div v-for="o in 4" :key="o" class="text item">
                                {{ "List item " + o }}
                            </div>
                        </el-card>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="With images" name="1">
                    <div class="block">
                        <el-row>
                            <el-col :span="8" :xs="11" v-for="(o, index) in 2" :key="o" style="margin: 5px">
                                <el-card :body-style="{ padding: '0px' }">
                                    <img :src="'/static/images/gallery/photo-' + index + '.jpg'" class="image" alt="card image" />
                                    <div style="padding: 14px">
                                        <span>Yummy hamburger</span>
                                        <div class="bottom clearfix">
                                            <time class="time">{{ currentDate }}</time>
                                            <el-button :link="true" class="button">Button</el-button>
                                        </div>
                                    </div>
                                </el-card>
                            </el-col>
                        </el-row>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </el-scrollbar>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"
import dayjs from "dayjs"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementCard",
    data() {
        return {
            currentDate: dayjs().format("DD/MM/YYYY"),
            code1: `
<el-card class="box-card">
  <div slot="header" class="clearfix">
    <span>Card name</span>
    <el-button style="float: right; padding: 3px 0" :link="true">Operation button</el-button>
  </div>
  <div v-for="o in 4" :key="o" class="text item">
    {{'List item ' + o }}
  </div>
</el-card>`,
            code2: `
<el-row>
  <el-col :span="8" v-for="(o, index) in 2" :key="o" :offset="index > 0 ? 2 : 0">
    <el-card :body-style="{ padding: '0px' }">
      <img src="~examples/assets/images/hamburger.png" class="image" alt="card image">
      <div style="padding: 14px;">
        <span>Yummy hamburger</span>
        <div class="bottom clearfix">
          <time class="time">{{ currentDate }}</time>
          <el-button :link="true" class="button">Operating button</el-button>
        </div>
      </div>
    </el-card>
  </el-col>
</el-row>

<style>
  .time {
    font-size: 13px;
    color: #999;
  }

  .bottom {
    margin-top: 13px;
    line-height: 12px;
  }

  .button {
    padding: 0;
    float: right;
  }

  .image {
    width: 100%;
    display: block;
  }

  .clearfix:before,
  .clearfix:after {
      display: table;
      content: "";
  }

  .clearfix:after {
      clear: both
  }
</style>

<script>
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
  data() {
    return {
      currentDate: new Date()
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

.block {
    padding: 15px;
}
.time {
    font-size: 13px;
    color: #999;
}

.bottom {
    margin-top: 13px;
    line-height: 12px;
}

.button {
    padding: 0;
    float: right;
}

.image {
    width: 100%;
    display: block;
}

.clearfix:before,
.clearfix:after {
    display: table;
    content: "";
}

.clearfix:after {
    clear: both;
}
</style>
