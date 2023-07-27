<template>
    <el-scrollbar class="page-element-transfer">
        <div class="page-header">
            <h1>
                Element Transfer
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/transfer" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Filterable" name="1">
                    <el-transfer
                        filterable
                        :filter-method="filterMethod"
                        filter-placeholder="State Abbreviations"
                        v-model="value2"
                        :data="data2"
                    >
                    </el-transfer>
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
    name: "ElementTransfer",
    data() {
        const generateData2 = _ => {
            const data = []
            const states = ["California", "Illinois", "Maryland", "Texas", "Florida", "Colorado", "Connecticut "]
            const initials = ["CA", "IL", "MD", "TX", "FL", "CO", "CT"]
            states.forEach((city, index) => {
                data.push({
                    label: city,
                    key: index,
                    initial: initials[index]
                })
            })
            return data
        }
        return {
            data2: generateData2(),
            value2: [],
            filterMethod(query, item) {
                return item.initial.toLowerCase().indexOf(query.toLowerCase()) > -1
            },
            code1: `
<template>
  <el-transfer
    filterable
    :filter-method="filterMethod"
    filter-placeholder="State Abbreviations"
    v-model="value2"
    :data="data2">
  </el-transfer>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      const generateData2 = _ => {
        const data = [];
        const states = ['California', 'Illinois', 'Maryland', 'Texas', 'Florida', 'Colorado', 'Connecticut '];
        const initials = ['CA', 'IL', 'MD', 'TX', 'FL', 'CO', 'CT'];
        states.forEach((city, index) => {
          data.push({
            label: city,
            key: index,
            initial: initials[index]
          });
        });
        return data;
      };
      return {
        data2: generateData2(),
        value2: [],
        filterMethod(query, item) {
          return item.initial.toLowerCase().indexOf(query.toLowerCase()) > -1;
        }
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
