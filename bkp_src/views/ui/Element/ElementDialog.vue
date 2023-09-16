<template>
    <el-scrollbar class="page-element-dialog">
        <div class="page-header">
            <h1>
                Element Dialog
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/dialog" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Customizations" name="1">
                    <!-- Table -->
                    <el-button :link="true" @click="dialogTableVisible = true">open a Table nested Dialog</el-button>

                    <el-dialog title="Shipping address" v-model="dialogTableVisible">
                        <el-table :data="gridData">
                            <el-table-column property="date" label="Date" width="150"></el-table-column>
                            <el-table-column property="name" label="Name" width="200"></el-table-column>
                            <el-table-column property="address" label="Address"></el-table-column>
                        </el-table>
                    </el-dialog>

                    <span style="margin-right: 20px"></span>

                    <!-- Form -->
                    <el-button :link="true" @click="dialogFormVisible = true">open a Form nested Dialog</el-button>

                    <el-dialog title="Shipping address" v-model="dialogFormVisible">
                        <el-form :model="form">
                            <el-form-item label="Promotion name" :label-width="formLabelWidth">
                                <el-input v-model="form.name" auto-complete="off"></el-input>
                            </el-form-item>
                            <el-form-item label="Zones" :label-width="formLabelWidth">
                                <el-select v-model="form.region" placeholder="Please select a zone">
                                    <el-option label="Zone No.1" value="shanghai"></el-option>
                                    <el-option label="Zone No.2" value="beijing"></el-option>
                                </el-select>
                            </el-form-item>
                        </el-form>
                        <span slot="footer" class="dialog-footer">
                            <el-button @click="dialogFormVisible = false">Cancel</el-button>
                            <el-button type="primary" @click="dialogFormVisible = false">Confirm</el-button>
                        </span>
                    </el-dialog>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Nested Dialog" name="1">
                    <el-button :link="true" @click="outerVisible = true">open the outer Dialog</el-button>

                    <el-dialog title="Outer Dialog" v-model="outerVisible">
                        <el-dialog width="30%" title="Inner Dialog" v-model="innerVisible" append-to-body> </el-dialog>
                        <div slot="footer" class="dialog-footer">
                            <el-button class="m-5" @click="outerVisible = false">Cancel</el-button>
                            <el-button class="m-5" type="primary" @click="innerVisible = true">open the inner Dialog</el-button>
                        </div>
                    </el-dialog>
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

import { defineComponent } from "vue"

export default defineComponent({
    name: "ElementDialog",
    data() {
        return {
            gridData: [
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
                },
                {
                    date: "2016-05-03",
                    name: "John Smith",
                    address: "No.1518,  Jinshajiang Road, Putuo District"
                }
            ],
            dialogTableVisible: false,
            dialogFormVisible: false,
            form: {
                name: "",
                region: "",
                date1: "",
                date2: "",
                delivery: false,
                type: [],
                resource: "",
                desc: ""
            },
            formLabelWidth: "120px",
            outerVisible: false,
            innerVisible: false,
            code1: `
<!-- Table -->
<el-button :link="true" @click="dialogTableVisible = true">open a Table nested Dialog</el-button>

<el-dialog title="Shipping address" v-model="dialogTableVisible">
  <el-table :data="gridData">
    <el-table-column property="date" label="Date" width="150"></el-table-column>
    <el-table-column property="name" label="Name" width="200"></el-table-column>
    <el-table-column property="address" label="Address"></el-table-column>
  </el-table>
</el-dialog>

<!-- Form -->
<el-button :link="true" @click="dialogFormVisible = true">open a Form nested Dialog</el-button>

<el-dialog title="Shipping address" v-model="dialogFormVisible">
  <el-form :model="form">
    <el-form-item label="Promotion name" :label-width="formLabelWidth">
      <el-input v-model="form.name" auto-complete="off"></el-input>
    </el-form-item>
    <el-form-item label="Zones" :label-width="formLabelWidth">
      <el-select v-model="form.region" placeholder="Please select a zone">
        <el-option label="Zone No.1" value="shanghai"></el-option>
        <el-option label="Zone No.2" value="beijing"></el-option>
      </el-select>
    </el-form-item>
  </el-form>
  <span slot="footer" class="dialog-footer">
    <el-button @click="dialogFormVisible = false">Cancel</el-button>
    <el-button type="primary" @click="dialogFormVisible = false">Confirm</el-button>
  </span>
</el-dialog>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        gridData: [{
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
        }, {
          date: '2016-05-03',
          name: 'John Smith',
          address: 'No.1518,  Jinshajiang Road, Putuo District'
        }],
        dialogTableVisible: false,
        dialogFormVisible: false,
        form: {
          name: '',
          region: '',
          date1: '',
          date2: '',
          delivery: false,
          type: [],
          resource: '',
          desc: ''
        },
        formLabelWidth: '120px'
      };
    }
  };
<\/script>`,
            code2: `
<template>
  <el-button :link="true" @click="outerVisible = true">open the outer Dialog</el-button>

  <el-dialog title="Outer Dialog" v-model="outerVisible">
    <el-dialog
        width="30%"
        title="Inner Dialog"
        v-model="innerVisible"
        append-to-body>
    </el-dialog>
    <div slot="footer" class="dialog-footer">
      <el-button @click="outerVisible = false">Cancel</el-button>
      <el-button type="primary" @click="innerVisible = true">open the inner Dialog</el-button>
    </div>
  </el-dialog>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        outerVisible: false,
        innerVisible: false
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
</style>
