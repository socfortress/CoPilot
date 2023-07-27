import Element from "../views/ui/Element/Element.vue"
import ElementButton from "../views/ui/Element/ElementButton.vue"
import ElementRadio from "../views/ui/Element/ElementRadio.vue"
import ElementCheckbox from "../views/ui/Element/ElementCheckbox.vue"
import ElementInput from "../views/ui/Element/ElementInput.vue"
import ElementInputNumber from "../views/ui/Element/ElementInputNumber.vue"
import ElementSelect from "../views/ui/Element/ElementSelect.vue"
import ElementCascader from "../views/ui/Element/ElementCascader.vue"
import ElementSwitch from "../views/ui/Element/ElementSwitch.vue"
import ElementSlider from "../views/ui/Element/ElementSlider.vue"
import ElementTimePicker from "../views/ui/Element/ElementTimePicker.vue"
import ElementDatePicker from "../views/ui/Element/ElementDatePicker.vue"
import ElementDateTimePicker from "../views/ui/Element/ElementDateTimePicker.vue"
import ElementUpload from "../views/ui/Element/ElementUpload.vue"
import ElementRate from "../views/ui/Element/ElementRate.vue"
import ElementColorPicker from "../views/ui/Element/ElementColorPicker.vue"
import ElementTransfer from "../views/ui/Element/ElementTransfer.vue"
import ElementForm from "../views/ui/Element/ElementForm.vue"
import ElementTag from "../views/ui/Element/ElementTag.vue"
import ElementProgress from "../views/ui/Element/ElementProgress.vue"
import ElementTree from "../views/ui/Element/ElementTree.vue"
import ElementPagination from "../views/ui/Element/ElementPagination.vue"
import ElementBadge from "../views/ui/Element/ElementBadge.vue"
import ElementAlert from "../views/ui/Element/ElementAlert.vue"
import ElementLoading from "../views/ui/Element/ElementLoading.vue"
import ElementMessage from "../views/ui/Element/ElementMessage.vue"
import ElementMessageBox from "../views/ui/Element/ElementMessageBox.vue"
import ElementNotification from "../views/ui/Element/ElementNotification.vue"
import ElementNavMenu from "../views/ui/Element/ElementNavMenu.vue"
import ElementTabs from "../views/ui/Element/ElementTabs.vue"
import ElementBreadcrumb from "../views/ui/Element/ElementBreadcrumb.vue"
import ElementDropdown from "../views/ui/Element/ElementDropdown.vue"
import ElementSteps from "../views/ui/Element/ElementSteps.vue"
import ElementDialog from "../views/ui/Element/ElementDialog.vue"
import ElementTooltip from "../views/ui/Element/ElementTooltip.vue"
import ElementPopover from "../views/ui/Element/ElementPopover.vue"
import ElementCard from "../views/ui/Element/ElementCard.vue"
import ElementCarousel from "../views/ui/Element/ElementCarousel.vue"
import ElementCollapse from "../views/ui/Element/ElementCollapse.vue"
import ElementTimeline from "../views/ui/Element/ElementTimeline.vue"

import layouts from "../layout"

export default {
    path: "/element",
    name: "element",
    component: Element,
    meta: {
        auth: true,
        layout: layouts.navLeft
    },
    children: [
        {
            path: "button",
            name: "button",
            component: ElementButton,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Button",
                tags: ["ui"]
            }
        },
        {
            path: "radio",
            name: "radio",
            component: ElementRadio,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Radio",
                tags: ["ui"]
            }
        },
        {
            path: "checkbox",
            name: "checkbox",
            component: ElementCheckbox,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Checkbox",
                tags: ["ui"]
            }
        },
        {
            path: "input",
            name: "input",
            component: ElementInput,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Input",
                tags: ["ui"]
            }
        },
        {
            path: "input-number",
            name: "input-number",
            component: ElementInputNumber,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Input Number",
                tags: ["ui"]
            }
        },
        {
            path: "select",
            name: "select",
            component: ElementSelect,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Select",
                tags: ["ui"]
            }
        },
        {
            path: "cascader",
            name: "cascader",
            component: ElementCascader,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Cascader",
                tags: ["ui"]
            }
        },
        {
            path: "switch",
            name: "switch",
            component: ElementSwitch,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Switch",
                tags: ["ui"]
            }
        },
        {
            path: "slider",
            name: "slider",
            component: ElementSlider,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Slider",
                tags: ["ui"]
            }
        },
        {
            path: "time-picker",
            name: "time-picker",
            component: ElementTimePicker,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Time Picker",
                tags: ["ui"]
            }
        },
        {
            path: "date-picker",
            name: "date-picker",
            component: ElementDatePicker,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Date Picker",
                tags: ["ui"]
            }
        },
        {
            path: "datetime-picker",
            name: "datetime-picker",
            component: ElementDateTimePicker,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Date Time Picker",
                tags: ["ui"]
            }
        },
        {
            path: "upload",
            name: "upload",
            component: ElementUpload,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Upload",
                tags: ["ui"]
            }
        },
        {
            path: "rate",
            name: "rate",
            component: ElementRate,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Rate",
                tags: ["ui"]
            }
        },
        {
            path: "color-picker",
            name: "color-picker",
            component: ElementColorPicker,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Color Picker",
                tags: ["ui"]
            }
        },
        {
            path: "transfer",
            name: "transfer",
            component: ElementTransfer,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Transfer",
                tags: ["ui"]
            }
        },
        {
            path: "form",
            name: "form",
            component: ElementForm,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Form",
                tags: ["ui"]
            }
        },
        {
            path: "tag",
            name: "tag",
            component: ElementTag,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Tag",
                tags: ["ui"]
            }
        },
        {
            path: "progress",
            name: "progress",
            component: ElementProgress,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Progress",
                tags: ["ui"]
            }
        },
        {
            path: "tree",
            name: "tree",
            component: ElementTree,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Tree",
                tags: ["ui"]
            }
        },
        {
            path: "pagination",
            name: "pagination",
            component: ElementPagination,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Pagination",
                tags: ["ui"]
            }
        },
        {
            path: "badge",
            name: "badge",
            component: ElementBadge,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Badge",
                tags: ["ui"]
            }
        },
        {
            path: "alert",
            name: "alert",
            component: ElementAlert,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Alert",
                tags: ["ui"]
            }
        },
        {
            path: "loading",
            name: "loading",
            component: ElementLoading,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Loading",
                tags: ["ui"]
            }
        },
        {
            path: "message",
            name: "message",
            component: ElementMessage,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Message",
                tags: ["ui"]
            }
        },
        {
            path: "message-box",
            name: "message-box",
            component: ElementMessageBox,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Message Box",
                tags: ["ui"]
            }
        },
        {
            path: "notification",
            name: "notification",
            component: ElementNotification,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Notification",
                tags: ["ui"]
            }
        },
        {
            path: "menu",
            name: "menu",
            component: ElementNavMenu,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element NavMenu",
                tags: ["ui"]
            }
        },
        {
            path: "tabs",
            name: "tabs",
            component: ElementTabs,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Tabs",
                tags: ["ui"]
            }
        },
        {
            path: "breadcrumb",
            name: "breadcrumb",
            component: ElementBreadcrumb,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Breadcrumb",
                tags: ["ui"]
            }
        },
        {
            path: "dropdown",
            name: "dropdown",
            component: ElementDropdown,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Dropdown",
                tags: ["ui"]
            }
        },
        {
            path: "steps",
            name: "steps",
            component: ElementSteps,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Steps",
                tags: ["ui"]
            }
        },
        {
            path: "dialog",
            name: "dialog",
            component: ElementDialog,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Dialog",
                tags: ["ui"]
            }
        },
        {
            path: "tooltip",
            name: "tooltip",
            component: ElementTooltip,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Tooltip",
                tags: ["ui"]
            }
        },
        {
            path: "popover",
            name: "popover",
            component: ElementPopover,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Popover",
                tags: ["ui"]
            }
        },
        {
            path: "card",
            name: "card",
            component: ElementCard,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Card",
                tags: ["ui"]
            }
        },
        {
            path: "carousel",
            name: "carousel",
            component: ElementCarousel,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Carousel",
                tags: ["ui"]
            }
        },
        {
            path: "collapse",
            name: "collapse",
            component: ElementCollapse,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Collapse",
                tags: ["ui"]
            }
        },
        {
            path: "timeline",
            name: "timeline",
            component: ElementTimeline,
            meta: {
                auth: true,
                layout: layouts.navLeft,
                searchable: true,
                title: "Element Timeline",
                tags: ["ui"]
            }
        }
    ]
}
