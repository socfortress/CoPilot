<template>
    <el-scrollbar class="page-element-timeline">
        <div class="page-header">
            <h1>
                Element Timeline
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/timeline" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Basic usage" name="1">
                    <div class="radio">
                        Order:
                        <el-radio-group v-model="reverse">
                            <el-radio :label="true">descending</el-radio>
                            <el-radio :label="false">ascending</el-radio>
                        </el-radio-group>
                    </div>

                    <el-timeline :reverse="reverse">
                        <el-timeline-item v-for="(activity, index) in activities" :key="index" :timestamp="activity.timestamp">
                            {{ activity.content }}
                        </el-timeline-item>
                    </el-timeline>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code1"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Custom node" name="1">
                    <el-timeline>
                        <el-timeline-item
                            v-for="(activity, index) in activities2"
                            :key="index"
                            :icon="activity.icon"
                            :type="activity.type"
                            :color="activity.color"
                            :size="activity.size"
                            :timestamp="activity.timestamp"
                        >
                            {{ activity.content }}
                        </el-timeline-item>
                    </el-timeline>
                </el-collapse-item>
                <el-collapse-item title="Code" name="2">
                    <pre v-highlightjs="code2"><code class="html"></code></pre>
                </el-collapse-item>
            </el-collapse>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Custom timestamp" name="1">
                    <el-timeline>
                        <el-timeline-item timestamp="2018/4/12" placement="top">
                            <el-card>
                                <h4>Update Github template</h4>
                                <p>Tom committed 2018/4/12 20:46</p>
                            </el-card>
                        </el-timeline-item>
                        <el-timeline-item timestamp="2018/4/3" placement="top">
                            <el-card>
                                <h4>Update Github template</h4>
                                <p>Tom committed 2018/4/3 20:46</p>
                            </el-card>
                        </el-timeline-item>
                        <el-timeline-item timestamp="2018/4/2" placement="top">
                            <el-card>
                                <h4>Update Github template</h4>
                                <p>Tom committed 2018/4/2 20:46</p>
                            </el-card>
                        </el-timeline-item>
                    </el-timeline>
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
    name: "ElementTimeline",
    data() {
        return {
            reverse: true,
            activities: [
                {
                    content: "Event start",
                    timestamp: "2018-04-15"
                },
                {
                    content: "Approved",
                    timestamp: "2018-04-13"
                },
                {
                    content: "Success",
                    timestamp: "2018-04-11"
                }
            ],
            activities2: [
                {
                    content: "Custom icon",
                    timestamp: "2018-04-12 20:46",
                    size: "large",
                    type: "primary",
                    icon: "el-icon-more"
                },
                {
                    content: "Custom color",
                    timestamp: "2018-04-03 20:46",
                    color: "#0bbd87"
                },
                {
                    content: "Custom size",
                    timestamp: "2018-04-03 20:46",
                    size: "large"
                },
                {
                    content: "Default node",
                    timestamp: "2018-04-03 20:46"
                }
            ],
            code1: `
<template>
  <div class="radio">
    Order:
    <el-radio-group v-model="reverse">
      <el-radio :label="true">descending</el-radio>
      <el-radio :label="false">ascending</el-radio>
    </el-radio-group>
  </div>

  <el-timeline :reverse="reverse">
    <el-timeline-item
      v-for="(activity, index) in activities"
      :key="index"
      :timestamp="activity.timestamp">
      {{activity.content}}
    </el-timeline-item>
  </el-timeline>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        reverse: true,
        activities: [{
          content: 'Event start',
          timestamp: '2018-04-15'
        }, {
          content: 'Approved',
          timestamp: '2018-04-13'
        }, {
          content: 'Success',
          timestamp: '2018-04-11'
        }]
      };
    }
<\/script>
`,
            code2: `
<template>
  <el-timeline>
    <el-timeline-item
      v-for="(activity, index) in activities"
      :key="index"
      :icon="activity.icon"
      :type="activity.type"
      :color="activity.color"
      :size="activity.size"
      :timestamp="activity.timestamp">
      {{activity.content}}
    </el-timeline-item>
  </el-timeline>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        activities: [{
          content: 'Custom icon',
          timestamp: '2018-04-12 20:46',
          size: 'large',
          type: 'primary',
          icon: 'el-icon-more'
        }, {
          content: 'Custom color',
          timestamp: '2018-04-03 20:46',
          color: '#0bbd87'
        }, {
          content: 'Custom size',
          timestamp: '2018-04-03 20:46',
          size: 'large'
        }, {
          content: 'Default node',
          timestamp: '2018-04-03 20:46'
        }]
      };
    }
  };
<\/script>
`,
            code3: `
<el-timeline>
	<el-timeline-item timestamp="2018/4/12" placement="top">
		<el-card>
		<h4>Update Github template</h4>
		<p>Tom committed 2018/4/12 20:46</p>
		</el-card>
	</el-timeline-item>
	<el-timeline-item timestamp="2018/4/3" placement="top">
		<el-card>
		<h4>Update Github template</h4>
		<p>Tom committed 2018/4/3 20:46</p>
		</el-card>
	</el-timeline-item>
	<el-timeline-item timestamp="2018/4/2" placement="top">
		<el-card>
		<h4>Update Github template</h4>
		<p>Tom committed 2018/4/2 20:46</p>
		</el-card>
	</el-timeline-item>
</el-timeline>
`
        }
    },
    components: { ThemePicker }
})
</script>

<style lang="scss" scoped>
.page-element-timeline .demo-box {
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
