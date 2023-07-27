<template>
    <el-scrollbar class="page-element-button">
        <div class="page-header">
            <h1>
                Element Button
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/button" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div>
                        <el-button>Default</el-button>
                        <el-button type="primary">Primary</el-button>
                        <el-button type="success">Success</el-button>
                        <el-button type="info">Info</el-button>
                        <el-button type="warning">Warning</el-button>
                        <el-button type="danger">Danger</el-button>
                    </div>

                    <div style="margin: 20px 0">
                        <el-button plain>Plain</el-button>
                        <el-button type="primary" plain>Primary</el-button>
                        <el-button type="success" plain>Success</el-button>
                        <el-button type="info" plain>Info</el-button>
                        <el-button type="warning" plain>Warning</el-button>
                        <el-button type="danger" plain>Danger</el-button>
                    </div>

                    <div>
                        <el-button round>Round</el-button>
                        <el-button type="primary" round>Primary</el-button>
                        <el-button type="success" round>Success</el-button>
                        <el-button type="info" round>Info</el-button>
                        <el-button type="warning" round>Warning</el-button>
                        <el-button type="danger" round>Danger</el-button>
                    </div>

                    <div class="mt-20">
                        <el-button icon="el-icon-search" circle></el-button>
                        <el-button type="primary" icon="el-icon-edit" circle></el-button>
                        <el-button type="success" icon="el-icon-check" circle></el-button>
                        <el-button type="info" icon="el-icon-message" circle></el-button>
                        <el-button type="warning" icon="el-icon-star-off" circle></el-button>
                        <el-button type="danger" icon="el-icon-delete" circle></el-button>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Text Button" name="1">
                    <el-button :link="true">Text Button</el-button>
                    <el-button :link="true" disabled>Text Button</el-button>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Icon Button" name="1">
                    <el-button type="primary" icon="el-icon-edit"></el-button>
                    <el-button type="primary" icon="el-icon-share"></el-button>
                    <el-button type="primary" icon="el-icon-delete"></el-button>
                    <el-button type="primary" icon="el-icon-search">Search</el-button>
                    <el-button type="primary">Upload<i class="el-icon-upload el-icon-right"></i></el-button>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code3"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <!--<div class="card-base card-shadow--medium demo-box bg-white">
			<el-collapse value="1">
				<el-collapse-item title="Button Group" name="1">
					<el-button-group>
						<el-button type="primary" icon="el-icon-arrow-left">Previous Page</el-button>
						<el-button type="primary">Next Page<i class="el-icon-arrow-right el-icon-right"></i></el-button>
					</el-button-group>
					&nbsp;
					<el-button-group>
						<el-button type="primary" icon="el-icon-edit"></el-button>
						<el-button type="primary" icon="el-icon-share"></el-button>
						<el-button type="primary" icon="el-icon-delete"></el-button>
					</el-button-group>
				</el-collapse-item>
				<el-collapse-item title="Code" name="2">
					<pre v-highlightjs="code4"><code class="html"></code></pre>
				</el-collapse-item>
			</el-collapse>
		</div>-->
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Sizes" name="1">
                    <div>
                        <el-button>Default</el-button>
                        <el-button size="large">Large</el-button>
                        <el-button size="small">Small</el-button>
                    </div>
                    <div style="margin-top: 20px">
                        <el-button round>Default</el-button>
                        <el-button size="large" round>Large</el-button>
                        <el-button size="small" round>Small</el-button>
                    </div>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code5"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
    </el-scrollbar>
</template>

<script>
import ThemePicker from "@/components/theme-picker.vue"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ElementButton",
    data() {
        return {
            code1: `
<div>
	<el-button>Default</el-button>
	<el-button type="primary">Primary</el-button>
	<el-button type="success">Success</el-button>
	<el-button type="info">Info</el-button>
	<el-button type="warning">Warning</el-button>
	<el-button type="danger">Danger</el-button>
</div>

<div style="margin: 20px 0">
	<el-button plain>Plain</el-button>
	<el-button type="primary" plain>Primary</el-button>
	<el-button type="success" plain>Success</el-button>
	<el-button type="info" plain>Info</el-button>
	<el-button type="warning" plain>Warning</el-button>
	<el-button type="danger" plain>Danger</el-button>
</div>

<div>
	<el-button round>Round</el-button>
	<el-button type="primary" round>Primary</el-button>
	<el-button type="success" round>Success</el-button>
	<el-button type="info" round>Info</el-button>
	<el-button type="warning" round>Warning</el-button>
	<el-button type="danger" round>Danger</el-button>
</div>

<div class="mt-20">
	<el-button icon="el-icon-search" circle></el-button>
	<el-button type="primary" icon="el-icon-edit" circle></el-button>
	<el-button type="success" icon="el-icon-check" circle></el-button>
	<el-button type="info" icon="el-icon-message" circle></el-button>
	<el-button type="warning" icon="el-icon-star-off" circle></el-button>
	<el-button type="danger" icon="el-icon-delete" circle></el-button>
</div>
`,
            code2: `
<el-button :link="true">Text Button</el-button>
<el-button :link="true" disabled>Text Button</el-button>
`,
            code3: `
<el-button type="primary" icon="el-icon-edit"></el-button>
<el-button type="primary" icon="el-icon-share"></el-button>
<el-button type="primary" icon="el-icon-delete"></el-button>
<el-button type="primary" icon="el-icon-search">Search</el-button>
<el-button type="primary">Upload<i class="el-icon-upload el-icon-right"></i></el-button>
`,
            code4: `
<el-button-group>
  <el-button type="primary" icon="el-icon-arrow-left">Previous Page</el-button>
  <el-button type="primary">Next Page<i class="el-icon-arrow-right el-icon-right"></i></el-button>
</el-button-group>
<el-button-group>
  <el-button type="primary" icon="el-icon-edit"></el-button>
  <el-button type="primary" icon="el-icon-share"></el-button>
  <el-button type="primary" icon="el-icon-delete"></el-button>
</el-button-group>
`,
            code5: `
<div>
  <el-button>Default</el-button>
  <el-button size="large">Large</el-button>
  <el-button size="small">Small</el-button>
</div>
<div style="margin-top: 20px">
  <el-button round>Default</el-button>
  <el-button size="large" round>Large</el-button>
  <el-button size="small" round>Small</el-button>
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
.page-element-button .demo-box {
    padding: 20px;
    margin-bottom: 20px;

    .el-button {
        margin: 10px;
    }
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
