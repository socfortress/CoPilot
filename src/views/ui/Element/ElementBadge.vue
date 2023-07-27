<template>
    <el-scrollbar class="page-element-badge">
        <div class="page-header">
            <h1>
                Element Badge
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/badge" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="block">
                        <el-badge :value="12" :max="10" class="item">
                            <el-button size="small">comments</el-button>
                        </el-badge>
                        <span style="margin-right: 30px"></span>
                        <el-badge is-dot class="item">
                            <el-button size="small">replies</el-button>
                        </el-badge>
                        <span style="margin-right: 30px"></span>
                        <el-dropdown trigger="click">
                            <span class="el-dropdown-link">
                                Click Me<i class="el-icon-caret-bottom el-icon--right"></i>
                            </span>
                            <el-dropdown-menu slot="dropdown">
                                <el-dropdown-item class="clearfix">
                                    comments
                                    <el-badge class="mark" value="new" />
                                </el-dropdown-item>
                                <el-dropdown-item class="clearfix">
                                    replies
                                    <el-badge class="mark" :value="3" />
                                </el-dropdown-item>
                            </el-dropdown-menu>
                        </el-dropdown>
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
    name: "ElementBadge",
    data() {
        return {
            value1: true,
            value2: true,
            code1: `
<el-badge :value="12" :max="10" class="item">
	<el-button size="small">comments</el-button>
</el-badge>
<span style="margin-right:30px;"></span>
<el-badge is-dot class="item">
	<el-button size="small">replies</el-button>
</el-badge>
<span style="margin-right:30px;"></span>
<el-dropdown trigger="click">
	<span class="el-dropdown-link">
		Click Me<i class="el-icon-caret-bottom el-icon--right"></i>
	</span>
	<el-dropdown-menu slot="dropdown">
		<el-dropdown-item class="clearfix">
			comments
			<el-badge class="mark" value="new" />
		</el-dropdown-item>
		<el-dropdown-item class="clearfix">
			replies
			<el-badge class="mark" :value="3" />
		</el-dropdown-item>
	</el-dropdown-menu>
</el-dropdown>
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
</style>
