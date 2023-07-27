<template>
    <div class="page-element-loading scrollable">
        <div class="page-header">
            <h1>
                Element Loading
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/loading" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Loading inside a container" name="1">
                    <el-table v-loading="loading" :data="tableData" style="width: 100%">
                        <el-table-column prop="date" label="Date" width="180"> </el-table-column>
                        <el-table-column prop="name" label="Name" width="180"> </el-table-column>
                        <el-table-column prop="address" label="Address"> </el-table-column>
                    </el-table>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Customization" name="1">
                    <el-table
                        v-loading="loading2"
                        element-loading-text="Loading..."
                        element-loading-spinner="el-icon-loading"
                        element-loading-background="rgba(0, 0, 0, 0.8)"
                        :data="tableData"
                        style="width: 100%"
                    >
                        <el-table-column prop="date" label="Date" width="180"> </el-table-column>
                        <el-table-column prop="name" label="Name" width="180"> </el-table-column>
                        <el-table-column prop="address" label="Address"> </el-table-column>
                    </el-table>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Full screen loading" name="1">
                    <el-button class="m-5" type="primary" @click="openFullScreen" v-loading.fullscreen.lock="fullscreenLoading">
                        As a directive
                    </el-button>
                    <el-button class="m-5" type="primary" @click="openFullScreen2"> As a service </el-button>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </div>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementLoading",
    data() {
        return {
            fullscreenLoading: false,
            tableData: [
                {
                    date: "2016-05-02",
                    name: "John Smith",
                    address: "No.1518,  Jinshajiang Road, Putuo District"
                },
                {
                    date: "2016-05-04",
                    name: "John Smith",
                    address: "No.1518,  Jinshajiang Road, Putuo District"
                },
                {
                    date: "2016-05-01",
                    name: "John Smith",
                    address: "No.1518,  Jinshajiang Road, Putuo District"
                }
            ],
            loading: true,
            loading2: true,
            code1: `
<template>
  <el-table
    v-loading="loading"
    :data="tableData"
    style="width: 100%">
    <el-table-column
      prop="date"
      label="Date"
      width="180">
    </el-table-column>
    <el-table-column
      prop="name"
      label="Name"
      width="180">
    </el-table-column>
    <el-table-column
      prop="address"
      label="Address">
    </el-table-column>
  </el-table>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        tableData: [{
          date: '2016-05-02',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }, {
          date: '2016-05-04',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }, {
          date: '2016-05-01',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }],
        loading: true
      };
    }
  };
<\/script>`,
            code2: `
<template>
  <el-table
    v-loading="loading2"
    element-loading-text="Loading..."
    element-loading-spinner="el-icon-loading"
    element-loading-background="rgba(0, 0, 0, 0.8)"
    :data="tableData"
    style="width: 100%">
    <el-table-column
      prop="date"
      label="Date"
      width="180">
    </el-table-column>
    <el-table-column
      prop="name"
      label="Name"
      width="180">
    </el-table-column>
    <el-table-column
      prop="address"
      label="Address">
    </el-table-column>
  </el-table>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        tableData: [{
          date: '2016-05-02',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }, {
          date: '2016-05-04',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }, {
          date: '2016-05-01',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }],
        loading2: true
      };
    }
  };
<\/script>
`,
            code3: `
<template>
  <el-button
    type="primary"
    @click="openFullScreen"
    v-loading.fullscreen.lock="fullscreenLoading">
    As a directive
  </el-button>
  <el-button
    type="primary"
    @click="openFullScreen2">
    As a service
  </el-button>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        fullscreenLoading: false
      }
    },
    methods: {
      openFullScreen() {
        this.fullscreenLoading = true;
        setTimeout(() => {
          this.fullscreenLoading = false;
        }, 2000);
      },
      openFullScreen2() {
        const loading = this.$loading({
          lock: true,
          text: 'Loading',
          spinner: 'el-icon-loading',
          background: 'rgba(0, 0, 0, 0.7)'
        });
        setTimeout(() => {
          loading.close();
        }, 2000);
      }
    }
  }
<\/script>
`
        }
    },
    methods: {
        openFullScreen() {
            this.fullscreenLoading = true
            setTimeout(() => {
                this.fullscreenLoading = false
            }, 2000)
        },
        openFullScreen2() {
            const loading = this.$loading({
                lock: true,
                text: "Loading",
                spinner: "el-icon-loading",
                background: "rgba(0, 0, 0, 0.7)"
            })
            setTimeout(() => {
                loading.close()
            }, 2000)
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
