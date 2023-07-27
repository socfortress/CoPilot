<template>
    <el-scrollbar class="page-element-popover">
        <div class="page-header">
            <h1>
                Element Popover
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/popover" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <el-popover
                        placement="top-start"
                        title="Title"
                        :width="200"
                        trigger="hover"
                        content="this is content, this is content, this is content"
                    >
                        <template #reference>
                            <el-button>Hover to activate</el-button>
                        </template>
                    </el-popover>

                    <el-popover
                        placement="bottom"
                        title="Title"
                        :width="200"
                        trigger="click"
                        content="this is content, this is content, this is content"
                    >
                        <template #reference>
                            <el-button>Click to activate</el-button>
                        </template>
                    </el-popover>

                    <el-popover
                        ref="popover"
                        placement="right"
                        title="Title"
                        :width="200"
                        trigger="focus"
                        content="this is content, this is content, this is content"
                    >
                        <template #reference>
                            <el-button>Focus to activate</el-button>
                        </template>
                    </el-popover>

                    <el-popover
                        ref="popover"
                        title="Title"
                        :width="200"
                        trigger="contextmenu"
                        content="this is content, this is content, this is content"
                    >
                        <template #reference>
                            <el-button>contextmenu to activate</el-button>
                        </template>
                    </el-popover>

                    <el-popover
                        :visible="visible"
                        placement="bottom"
                        title="Title"
                        :width="200"
                        content="this is content, this is content, this is content"
                    >
                        <template #reference>
                            <el-button @click="visible = !visible">Manual to activate</el-button>
                        </template>
                    </el-popover>
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
    name: "ElementPopover",
    data() {
        return {
            gridData: [
                {
                    date: "2016-05-02",
                    name: "Jack",
                    address: "New York City"
                },
                {
                    date: "2016-05-04",
                    name: "Jack",
                    address: "New York City"
                },
                {
                    date: "2016-05-01",
                    name: "Jack",
                    address: "New York City"
                },
                {
                    date: "2016-05-03",
                    name: "Jack",
                    address: "New York City"
                }
            ],
            visible: false,
            code1: `
			<el-popover
    placement="top-start"
    title="Title"
    :width="200"
    trigger="hover"
    content="this is content, this is content, this is content"
  >
    <template #reference>
      <el-button>Hover to activate</el-button>
    </template>
  </el-popover>

  <el-popover
    placement="bottom"
    title="Title"
    :width="200"
    trigger="click"
    content="this is content, this is content, this is content"
  >
    <template #reference>
      <el-button>Click to activate</el-button>
    </template>
  </el-popover>

  <el-popover
    ref="popover"
    placement="right"
    title="Title"
    :width="200"
    trigger="focus"
    content="this is content, this is content, this is content"
  >
    <template #reference>
      <el-button>Focus to activate</el-button>
    </template>
  </el-popover>

  <el-popover
    ref="popover"
    title="Title"
    :width="200"
    trigger="contextmenu"
    content="this is content, this is content, this is content"
  >
    <template #reference>
      <el-button>contextmenu to activate</el-button>
    </template>
  </el-popover>

  <el-popover
    :visible="visible"
    placement="bottom"
    title="Title"
    :width="200"
    content="this is content, this is content, this is content"
  >
    <template #reference>
      <el-button @click="visible = !visible">Manual to activate</el-button>
    </template>
  </el-popover>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        gridData: [{
          date: '2016-05-02',
          name: 'Jack',
          address: 'New York City'
        }, {
          date: '2016-05-04',
          name: 'Jack',
          address: 'New York City'
        }, {
          date: '2016-05-01',
          name: 'Jack',
          address: 'New York City'
        }, {
          date: '2016-05-03',
          name: 'Jack',
          address: 'New York City'
        }]
      };
    }
  };
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
