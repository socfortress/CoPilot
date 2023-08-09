<template>
    <el-scrollbar class="page-element-radio">
        <div class="page-header">
            <h1>
                Element Radio
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/radio" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <el-radio v-model="radio" label="1">Option A</el-radio>
                    <el-radio v-model="radio" label="2">Option B</el-radio>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white hidden-xs-only">
            <el-collapse value="1">
                <el-collapse-item title="Button style" name="1">
                    <div>
                        <el-radio-group v-model="radio3">
                            <el-radio-button label="New York"></el-radio-button>
                            <el-radio-button label="Washington"></el-radio-button>
                            <el-radio-button label="Los Angeles"></el-radio-button>
                            <el-radio-button label="Chicago"></el-radio-button>
                        </el-radio-group>
                    </div>
                    <div style="margin-top: 20px">
                        <el-radio-group v-model="radio4" size="default">
                            <el-radio-button label="New York"></el-radio-button>
                            <el-radio-button label="Washington"></el-radio-button>
                            <el-radio-button label="Los Angeles"></el-radio-button>
                            <el-radio-button label="Chicago"></el-radio-button>
                        </el-radio-group>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="With borders" name="1">
                    <div>
                        <el-radio v-model="radio7" label="1" border>Option A</el-radio>
                        <el-radio v-model="radio7" label="2" border>Option B</el-radio>
                    </div>
                    <div style="margin-top: 20px">
                        <el-radio v-model="radio8" label="1" border size="default">Option A</el-radio>
                        <el-radio v-model="radio8" label="2" border size="default">Option B</el-radio>
                    </div>
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
import { defineComponent } from "vue"

export default defineComponent({
    name: "ElementRadio",
    data() {
        return {
            radio: "1",
            radio3: "New York",
            radio4: "New York",
            radio5: "New York",
            radio6: "New York",
            radio7: "1",
            radio8: "1",
            radio9: "1",
            radio10: "1",
            code1: `
<el-radio v-model="radio" label="1">Option A</el-radio>
<el-radio v-model="radio" label="2">Option B</el-radio>
`,
            code2: `
<div>
    <el-radio-group v-model="radio3">
		<el-radio-button label="New York"></el-radio-button>
		<el-radio-button label="Washington"></el-radio-button>
		<el-radio-button label="Los Angeles"></el-radio-button>
		<el-radio-button label="Chicago"></el-radio-button>
    </el-radio-group>
</div>
<div style="margin-top: 20px">
	<el-radio-group v-model="radio4" size="default">
		<el-radio-button label="New York" ></el-radio-button>
		<el-radio-button label="Washington"></el-radio-button>
		<el-radio-button label="Los Angeles"></el-radio-button>
		<el-radio-button label="Chicago"></el-radio-button>
	</el-radio-group>
</div>
`,
            code3: `
<div>
	<el-radio v-model="radio7" label="1" border>Option A</el-radio>
	<el-radio v-model="radio7" label="2" border>Option B</el-radio>
</div>
<div style="margin-top: 20px">
	<el-radio v-model="radio8" label="1" border size="default">Option A</el-radio>
	<el-radio v-model="radio8" label="2" border size="default">Option B</el-radio>
</div>
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
