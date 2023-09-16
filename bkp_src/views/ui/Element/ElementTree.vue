<template>
    <el-scrollbar class="page-element-tree">
        <div class="page-header">
            <h1>
                Element Tree
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/tree" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Tree node filtering" name="1">
                    <el-input placeholder="Filter keyword" v-model="filterText"> </el-input>
                    &nbsp;
                    <el-tree
                        class="filter-tree"
                        :data="data2"
                        :props="defaultProps"
                        default-expand-all
                        show-checkbox
                        :filter-node-method="filterNode"
                        ref="tree2"
                    >
                    </el-tree>
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

import { defineComponent } from "vue"

export default defineComponent({
    name: "ElementTree",
    watch: {
        filterText(val) {
            this.$refs.tree2.filter(val)
        }
    },

    methods: {
        filterNode(value, data) {
            if (!value) return true
            return data.label.indexOf(value) !== -1
        }
    },
    data() {
        return {
            filterText: "",
            data2: [
                {
                    id: 1,
                    label: "Level one 1",
                    children: [
                        {
                            id: 4,
                            label: "Level two 1-1",
                            children: [
                                {
                                    id: 9,
                                    label: "Level three 1-1-1"
                                },
                                {
                                    id: 10,
                                    label: "Level three 1-1-2"
                                }
                            ]
                        }
                    ]
                },
                {
                    id: 2,
                    label: "Level one 2",
                    children: [
                        {
                            id: 5,
                            label: "Level two 2-1"
                        },
                        {
                            id: 6,
                            label: "Level two 2-2"
                        }
                    ]
                },
                {
                    id: 3,
                    label: "Level one 3",
                    children: [
                        {
                            id: 7,
                            label: "Level two 3-1"
                        },
                        {
                            id: 8,
                            label: "Level two 3-2"
                        }
                    ]
                }
            ],
            defaultProps: {
                children: "children",
                label: "label"
            },
            code1: `
<el-input
  placeholder="Filter keyword"
  v-model="filterText">
</el-input>

<el-tree
  class="filter-tree"
  :data="data2"
  :props="defaultProps"
  default-expand-all
  show-checkbox
  :filter-node-method="filterNode"
  ref="tree2">
</el-tree>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    watch: {
      filterText(val) {
        this.$refs.tree2.filter(val);
      }
    },

    methods: {
      filterNode(value, data) {
        if (!value) return true;
        return data.label.indexOf(value) !== -1;
      }
    },

    data() {
      return {
        filterText: '',
        data2: [{
          id: 1,
          label: 'Level one 1',
          children: [{
            id: 4,
            label: 'Level two 1-1',
            children: [{
              id: 9,
              label: 'Level three 1-1-1'
            }, {
              id: 10,
              label: 'Level three 1-1-2'
            }]
          }]
        }, {
          id: 2,
          label: 'Level one 2',
          children: [{
            id: 5,
            label: 'Level two 2-1'
          }, {
            id: 6,
            label: 'Level two 2-2'
          }]
        }, {
          id: 3,
          label: 'Level one 3',
          children: [{
            id: 7,
            label: 'Level two 3-1'
          }, {
            id: 8,
            label: 'Level two 3-2'
          }]
        }],
        defaultProps: {
          children: 'children',
          label: 'label'
        }
      };
    }
  };
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
