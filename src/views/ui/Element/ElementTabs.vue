<template>
    <el-scrollbar class="page-element-tabs">
        <div class="page-header">
            <h1>
                Element Tabs
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/tabs" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Tab position" name="1">
                    <el-radio-group v-model="tabPosition" style="margin-bottom: 30px">
                        <el-radio-button label="top">top</el-radio-button>
                        <el-radio-button label="right">right</el-radio-button>
                        <el-radio-button label="bottom">bottom</el-radio-button>
                        <el-radio-button label="left">left</el-radio-button>
                    </el-radio-group>

                    <el-tabs :tab-position="tabPosition" style="height: 200px">
                        <el-tab-pane label="User">User</el-tab-pane>
                        <el-tab-pane label="Config">Config</el-tab-pane>
                        <el-tab-pane label="Role">Role</el-tab-pane>
                        <el-tab-pane label="Task">Task</el-tab-pane>
                    </el-tabs>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Custom Tab" name="1">
                    <el-tabs type="border-card">
                        <el-tab-pane>
                            <span slot="label"><i class="el-icon-date"></i> Route</span>
                            Route
                        </el-tab-pane>
                        <el-tab-pane label="Config">Config</el-tab-pane>
                        <el-tab-pane label="Role">Role</el-tab-pane>
                        <el-tab-pane label="Task">Task</el-tab-pane>
                    </el-tabs>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Customized trigger button of new tab" name="1">
                    <div style="margin-bottom: 20px">
                        <el-button size="small" @click="addTab(editableTabsValue2)"> add tab </el-button>
                    </div>
                    <el-tabs v-model="editableTabsValue2" type="card" closable @tab-remove="removeTab">
                        <el-tab-pane
                            v-for="item in editableTabs2"
                            :key="item.name"
                            :label="item.title"
                            :name="item.name"
                        >
                            {{ item.content }}
                        </el-tab-pane>
                    </el-tabs>
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
    name: "ElementTabs",
    methods: {
        addTab(targetName) {
            let newTabName = ++this.tabIndex + ""
            this.editableTabs2.push({
                title: "New Tab",
                name: newTabName,
                content: "New Tab content"
            })
            this.editableTabsValue2 = newTabName
        },
        removeTab(targetName) {
            let tabs = this.editableTabs2
            let activeName = this.editableTabsValue2
            if (activeName === targetName) {
                tabs.forEach((tab, index) => {
                    if (tab.name === targetName) {
                        let nextTab = tabs[index + 1] || tabs[index - 1]
                        if (nextTab) {
                            activeName = nextTab.name
                        }
                    }
                })
            }

            this.editableTabsValue2 = activeName
            this.editableTabs2 = tabs.filter(tab => tab.name !== targetName)
        }
    },
    data() {
        return {
            editableTabsValue2: "2",
            editableTabs2: [
                {
                    title: "Tab 1",
                    name: "1",
                    content: "Tab 1 content"
                },
                {
                    title: "Tab 2",
                    name: "2",
                    content: "Tab 2 content"
                }
            ],
            tabIndex: 2,
            tabPosition: "top",
            code1: `
<template>
  <el-radio-group v-model="tabPosition" style="margin-bottom: 30px;">
    <el-radio-button label="top">top</el-radio-button>
    <el-radio-button label="right">right</el-radio-button>
    <el-radio-button label="bottom">bottom</el-radio-button>
    <el-radio-button label="left">left</el-radio-button>
  </el-radio-group>

  <el-tabs :tab-position="tabPosition" style="height: 200px;">
    <el-tab-pane label="User">User</el-tab-pane>
    <el-tab-pane label="Config">Config</el-tab-pane>
    <el-tab-pane label="Role">Role</el-tab-pane>
    <el-tab-pane label="Task">Task</el-tab-pane>
  </el-tabs>
</template>
<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        tabPosition: 'top'
      };
    }
  };
<\/script>
`,
            code2: `
<el-tabs type="border-card">
  <el-tab-pane>
    <span slot="label"><i class="el-icon-date"></i> Route</span>
    Route
  </el-tab-pane>
  <el-tab-pane label="Config">Config</el-tab-pane>
  <el-tab-pane label="Role">Role</el-tab-pane>
  <el-tab-pane label="Task">Task</el-tab-pane>
</el-tabs>
`,
            code3: `
<div style="margin-bottom: 20px;">
  <el-button
    size="small"
    @click="addTab(editableTabsValue2)"
  >
    add tab
  </el-button>
</div>
<el-tabs v-model="editableTabsValue2" type="card" closable @tab-remove="removeTab">
  <el-tab-pane
    v-for="(item, index) in editableTabs2"
    :key="item.name"
    :label="item.title"
    :name="item.name"
  >
    {{item.content}}
  </el-tab-pane>
</el-tabs>
<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        editableTabsValue2: '2',
        editableTabs2: [{
          title: 'Tab 1',
          name: '1',
          content: 'Tab 1 content'
        }, {
          title: 'Tab 2',
          name: '2',
          content: 'Tab 2 content'
        }],
        tabIndex: 2
      }
    },
    methods: {
      addTab(targetName) {
        let newTabName = ++this.tabIndex + '';
        this.editableTabs2.push({
          title: 'New Tab',
          name: newTabName,
          content: 'New Tab content'
        });
        this.editableTabsValue2 = newTabName;
      },
      removeTab(targetName) {
        let tabs = this.editableTabs2;
        let activeName = this.editableTabsValue2;
        if (activeName === targetName) {
          tabs.forEach((tab, index) => {
            if (tab.name === targetName) {
              let nextTab = tabs[index + 1] || tabs[index - 1];
              if (nextTab) {
                activeName = nextTab.name;
              }
            }
          });
        }

        this.editableTabsValue2 = activeName;
        this.editableTabs2 = tabs.filter(tab => tab.name !== targetName);
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
.page-element-tabs .el-radio-button__inner {
    padding: 10px 14px;
}
</style>
