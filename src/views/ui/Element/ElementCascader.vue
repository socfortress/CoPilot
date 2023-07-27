<template>
    <el-scrollbar class="page-element-cascader">
        <div class="page-header">
            <h1>
                Element Cascader
                <theme-picker style="float: right"></theme-picker>
            </h1>
            <h4>
                <a href="http://element.eleme.io/#/en-US/component/cascader" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
        </div>
        <div class="card-base card-shadow--medium demo-box bg-white">
            <el-collapse value="1">
                <el-collapse-item title="Filterable" name="1">
                    <el-cascader
                        placeholder="Try searching: Guide"
                        :options="options"
                        filterable
                        change-on-select
                    ></el-cascader>
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
    name: "ElementCascader",
    data() {
        return {
            options: [
                {
                    value: "guide",
                    label: "Guide",
                    children: [
                        {
                            value: "disciplines",
                            label: "Disciplines",
                            children: [
                                {
                                    value: "consistency",
                                    label: "Consistency"
                                },
                                {
                                    value: "feedback",
                                    label: "Feedback"
                                },
                                {
                                    value: "efficiency",
                                    label: "Efficiency"
                                },
                                {
                                    value: "controllability",
                                    label: "Controllability"
                                }
                            ]
                        },
                        {
                            value: "navigation",
                            label: "Navigation",
                            children: [
                                {
                                    value: "side nav",
                                    label: "Side Navigation"
                                },
                                {
                                    value: "top nav",
                                    label: "Top Navigation"
                                }
                            ]
                        }
                    ]
                },
                {
                    value: "component",
                    label: "Component",
                    children: [
                        {
                            value: "basic",
                            label: "Basic",
                            children: [
                                {
                                    value: "layout",
                                    label: "Layout"
                                },
                                {
                                    value: "color",
                                    label: "Color"
                                },
                                {
                                    value: "typography",
                                    label: "Typography"
                                },
                                {
                                    value: "icon",
                                    label: "Icon"
                                },
                                {
                                    value: "button",
                                    label: "Button"
                                }
                            ]
                        },
                        {
                            value: "form",
                            label: "Form",
                            children: [
                                {
                                    value: "radio",
                                    label: "Radio"
                                },
                                {
                                    value: "checkbox",
                                    label: "Checkbox"
                                },
                                {
                                    value: "input",
                                    label: "Input"
                                },
                                {
                                    value: "input-number",
                                    label: "InputNumber"
                                },
                                {
                                    value: "select",
                                    label: "Select"
                                },
                                {
                                    value: "cascader",
                                    label: "Cascader"
                                },
                                {
                                    value: "switch",
                                    label: "Switch"
                                },
                                {
                                    value: "slider",
                                    label: "Slider"
                                },
                                {
                                    value: "time-picker",
                                    label: "TimePicker"
                                },
                                {
                                    value: "date-picker",
                                    label: "DatePicker"
                                },
                                {
                                    value: "datetime-picker",
                                    label: "DateTimePicker"
                                },
                                {
                                    value: "upload",
                                    label: "Upload"
                                },
                                {
                                    value: "rate",
                                    label: "Rate"
                                },
                                {
                                    value: "form",
                                    label: "Form"
                                }
                            ]
                        },
                        {
                            value: "data",
                            label: "Data",
                            children: [
                                {
                                    value: "table",
                                    label: "Table"
                                },
                                {
                                    value: "tag",
                                    label: "Tag"
                                },
                                {
                                    value: "progress",
                                    label: "Progress"
                                },
                                {
                                    value: "tree",
                                    label: "Tree"
                                },
                                {
                                    value: "pagination",
                                    label: "Pagination"
                                },
                                {
                                    value: "badge",
                                    label: "Badge"
                                }
                            ]
                        },
                        {
                            value: "notice",
                            label: "Notice",
                            children: [
                                {
                                    value: "alert",
                                    label: "Alert"
                                },
                                {
                                    value: "loading",
                                    label: "Loading"
                                },
                                {
                                    value: "message",
                                    label: "Message"
                                },
                                {
                                    value: "message-box",
                                    label: "MessageBox"
                                },
                                {
                                    value: "notification",
                                    label: "Notification"
                                }
                            ]
                        },
                        {
                            value: "navigation",
                            label: "Navigation",
                            children: [
                                {
                                    value: "menu",
                                    label: "NavMenu"
                                },
                                {
                                    value: "tabs",
                                    label: "Tabs"
                                },
                                {
                                    value: "breadcrumb",
                                    label: "Breadcrumb"
                                },
                                {
                                    value: "dropdown",
                                    label: "Dropdown"
                                },
                                {
                                    value: "steps",
                                    label: "Steps"
                                }
                            ]
                        },
                        {
                            value: "others",
                            label: "Others",
                            children: [
                                {
                                    value: "dialog",
                                    label: "Dialog"
                                },
                                {
                                    value: "tooltip",
                                    label: "Tooltip"
                                },
                                {
                                    value: "popover",
                                    label: "Popover"
                                },
                                {
                                    value: "card",
                                    label: "Card"
                                },
                                {
                                    value: "carousel",
                                    label: "Carousel"
                                },
                                {
                                    value: "collapse",
                                    label: "Collapse"
                                }
                            ]
                        }
                    ]
                },
                {
                    value: "resource",
                    label: "Resource",
                    children: [
                        {
                            value: "axure",
                            label: "Axure Components"
                        },
                        {
                            value: "sketch",
                            label: "Sketch Templates"
                        },
                        {
                            value: "docs",
                            label: "Design Documentation"
                        }
                    ]
                }
            ],
            code1: `
<template>
  <el-cascader
    placeholder="Try searching: Guide"
    :options="options"
    filterable
    change-on-select
  ></el-cascader>
</template>

<script>
  import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    data() {
      return {
        options: [{
          value: 'guide',
          label: 'Guide',
          children: [{
            value: 'disciplines',
            label: 'Disciplines',
            children: [{
              value: 'consistency',
              label: 'Consistency'
            }, {
              value: 'feedback',
              label: 'Feedback'
            }, {
              value: 'efficiency',
              label: 'Efficiency'
            }, {
              value: 'controllability',
              label: 'Controllability'
            }]
          }, {
            value: 'navigation',
            label: 'Navigation',
            children: [{
              value: 'side nav',
              label: 'Side Navigation'
            }, {
              value: 'top nav',
              label: 'Top Navigation'
            }]
          }]
        }, {
          value: 'component',
          label: 'Component',
          children: [{
            value: 'basic',
            label: 'Basic',
            children: [{
              value: 'layout',
              label: 'Layout'
            }, {
              value: 'color',
              label: 'Color'
            }, {
              value: 'typography',
              label: 'Typography'
            }, {
              value: 'icon',
              label: 'Icon'
            }, {
              value: 'button',
              label: 'Button'
            }]
          }, {
            value: 'form',
            label: 'Form',
            children: [{
              value: 'radio',
              label: 'Radio'
            }, {
              value: 'checkbox',
              label: 'Checkbox'
            }, {
              value: 'input',
              label: 'Input'
            }, {
              value: 'input-number',
              label: 'InputNumber'
            }, {
              value: 'select',
              label: 'Select'
            }, {
              value: 'cascader',
              label: 'Cascader'
            }, {
              value: 'switch',
              label: 'Switch'
            }, {
              value: 'slider',
              label: 'Slider'
            }, {
              value: 'time-picker',
              label: 'TimePicker'
            }, {
              value: 'date-picker',
              label: 'DatePicker'
            }, {
              value: 'datetime-picker',
              label: 'DateTimePicker'
            }, {
              value: 'upload',
              label: 'Upload'
            }, {
              value: 'rate',
              label: 'Rate'
            }, {
              value: 'form',
              label: 'Form'
            }]
          }, {
            value: 'data',
            label: 'Data',
            children: [{
              value: 'table',
              label: 'Table'
            }, {
              value: 'tag',
              label: 'Tag'
            }, {
              value: 'progress',
              label: 'Progress'
            }, {
              value: 'tree',
              label: 'Tree'
            }, {
              value: 'pagination',
              label: 'Pagination'
            }, {
              value: 'badge',
              label: 'Badge'
            }]
          }, {
            value: 'notice',
            label: 'Notice',
            children: [{
              value: 'alert',
              label: 'Alert'
            }, {
              value: 'loading',
              label: 'Loading'
            }, {
              value: 'message',
              label: 'Message'
            }, {
              value: 'message-box',
              label: 'MessageBox'
            }, {
              value: 'notification',
              label: 'Notification'
            }]
          }, {
            value: 'navigation',
            label: 'Navigation',
            children: [{
              value: 'menu',
              label: 'NavMenu'
            }, {
              value: 'tabs',
              label: 'Tabs'
            }, {
              value: 'breadcrumb',
              label: 'Breadcrumb'
            }, {
              value: 'dropdown',
              label: 'Dropdown'
            }, {
              value: 'steps',
              label: 'Steps'
            }]
          }, {
            value: 'others',
            label: 'Others',
            children: [{
              value: 'dialog',
              label: 'Dialog'
            }, {
              value: 'tooltip',
              label: 'Tooltip'
            }, {
              value: 'popover',
              label: 'Popover'
            }, {
              value: 'card',
              label: 'Card'
            }, {
              value: 'carousel',
              label: 'Carousel'
            }, {
              value: 'collapse',
              label: 'Collapse'
            }]
          }]
        }, {
          value: 'resource',
          label: 'Resource',
          children: [{
            value: 'axure',
            label: 'Axure Components'
          }, {
            value: 'sketch',
            label: 'Sketch Templates'
          }, {
            value: 'docs',
            label: 'Design Documentation'
          }]
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
