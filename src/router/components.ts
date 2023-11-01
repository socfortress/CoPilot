import { UserRole } from "@/types/auth.d"

export default {
	path: "/components",
	redirect: "/components/avatar",
	meta: {
		auth: true,
		roles: UserRole.All
	},
	children: [
		{
			path: "avatar",
			name: "Components-Avatar",
			component: () => import("@/views/Components/Avatar.vue"),
			meta: { title: "Components Avatar" }
		},
		{
			path: "button",
			name: "Components-Button",
			component: () => import("@/views/Components/Button.vue"),
			meta: { title: "Components Button" }
		},
		{
			path: "card",
			name: "Components-Card",
			component: () => import("@/views/Components/Card.vue"),
			meta: { title: "Components Card" }
		},
		{
			path: "carousel",
			name: "Components-Carousel",
			component: () => import("@/views/Components/Carousel.vue"),
			meta: { title: "Components Carousel" }
		},
		{
			path: "collapse",
			name: "Components-Collapse",
			component: () => import("@/views/Components/Collapse.vue"),
			meta: { title: "Components Collapse" }
		},
		{
			path: "divider",
			name: "Components-Divider",
			component: () => import("@/views/Components/Divider.vue"),
			meta: { title: "Components Divider" }
		},
		{
			path: "dropdown",
			name: "Components-Dropdown",
			component: () => import("@/views/Components/Dropdown.vue"),
			meta: { title: "Components Dropdown" }
		},
		{
			path: "ellipsis",
			name: "Components-Ellipsis",
			component: () => import("@/views/Components/Ellipsis.vue"),
			meta: { title: "Components Ellipsis" }
		},
		{
			path: "gradienttext",
			name: "Components-GradientText",
			component: () => import("@/views/Components/GradientText.vue"),
			meta: { title: "Components Gradient Text" }
		},
		{
			path: "icon",
			name: "Components-Icon",
			component: () => import("@/views/Components/Icon.vue"),
			meta: { title: "Components Icon" }
		},
		{
			path: "pageheader",
			name: "Components-PageHeader",
			component: () => import("@/views/Components/PageHeader.vue"),
			meta: { title: "Components Page Header" }
		},
		{
			path: "tag",
			name: "Components-Tag",
			component: () => import("@/views/Components/Tag.vue"),
			meta: { title: "Components Tag" }
		},
		{
			path: "typography",
			name: "Components-Typography",
			component: () => import("@/views/Components/Typography.vue"),
			meta: { title: "Components Typography" }
		},
		{
			path: "watermark",
			name: "Components-Watermark",
			component: () => import("@/views/Components/Watermark.vue"),
			meta: { title: "Components Watermark" }
		},
		{
			path: "autocomplete",
			name: "Components-AutoComplete",
			component: () => import("@/views/Components/AutoComplete.vue"),
			meta: { title: "Components Auto Complete" }
		},
		{
			path: "cascader",
			name: "Components-Cascader",
			component: () => import("@/views/Components/Cascader.vue"),
			meta: { title: "Components Cascader" }
		},
		{
			path: "colorpicker",
			name: "Components-ColorPicker",
			component: () => import("@/views/Components/ColorPicker.vue"),
			meta: { title: "Components Color Picker" }
		},
		{
			path: "checkbox",
			name: "Components-Checkbox",
			component: () => import("@/views/Components/Checkbox.vue"),
			meta: { title: "Components Checkbox" }
		},
		{
			path: "datepicker",
			name: "Components-DatePicker",
			component: () => import("@/views/Components/DatePicker.vue"),
			meta: { title: "Components Date Picker" }
		},
		{
			path: "dynamicinput",
			name: "Components-DynamicInput",
			component: () => import("@/views/Components/DynamicInput.vue"),
			meta: { title: "Components Dynamic Input" }
		},
		{
			path: "dynamictags",
			name: "Components-DynamicTags",
			component: () => import("@/views/Components/DynamicTags.vue"),
			meta: { title: "Components Dynamic Tags" }
		},
		{
			path: "form",
			name: "Components-Form",
			component: () => import("@/views/Components/Form.vue"),
			meta: { title: "Components Form" }
		},
		{
			path: "input",
			name: "Components-Input",
			component: () => import("@/views/Components/Input.vue"),
			meta: { title: "Components Input" }
		},
		{
			path: "inputnumber",
			name: "Components-InputNumber",
			component: () => import("@/views/Components/InputNumber.vue"),
			meta: { title: "Components Input Number" }
		},
		{
			path: "mention",
			name: "Components-Mention",
			component: () => import("@/views/Components/Mention.vue"),
			meta: { title: "Components Mention" }
		},
		{
			path: "radio",
			name: "Components-Radio",
			component: () => import("@/views/Components/Radio.vue"),
			meta: { title: "Components Radio" }
		},
		{
			path: "rate",
			name: "Components-Rate",
			component: () => import("@/views/Components/Rate.vue"),
			meta: { title: "Components Rate" }
		},
		{
			path: "select",
			name: "Components-Select",
			component: () => import("@/views/Components/Select.vue"),
			meta: { title: "Components Select" }
		},
		{
			path: "slider",
			name: "Components-Slider",
			component: () => import("@/views/Components/Slider.vue"),
			meta: { title: "Components Slider" }
		},
		{
			path: "switch",
			name: "Components-Switch",
			component: () => import("@/views/Components/Switch.vue"),
			meta: { title: "Components Switch" }
		},
		{
			path: "timepicker",
			name: "Components-TimePicker",
			component: () => import("@/views/Components/TimePicker.vue"),
			meta: { title: "Components Time Picker" }
		},
		{
			path: "transfer",
			name: "Components-Transfer",
			component: () => import("@/views/Components/Transfer.vue"),
			meta: { title: "Components Transfer" }
		},
		{
			path: "treeselect",
			name: "Components-TreeSelect",
			component: () => import("@/views/Components/TreeSelect.vue"),
			meta: { title: "Components Tree Select" }
		},
		{
			path: "upload",
			name: "Components-Upload",
			component: () => import("@/views/Components/Upload.vue"),
			meta: { title: "Components Upload" }
		},
		{
			path: "calendar",
			name: "Components-Calendar",
			component: () => import("@/views/Components/Calendar.vue"),
			meta: { title: "Components Calendar" }
		},
		{
			path: "countdown",
			name: "Components-Countdown",
			component: () => import("@/views/Components/Countdown.vue"),
			meta: { title: "Components Countdown" }
		},
		{
			path: "datatable",
			name: "Components-DataTable",
			component: () => import("@/views/Components/DataTable.vue"),
			meta: { title: "Components Data Table" }
		},
		{
			path: "descriptions",
			name: "Components-Descriptions",
			component: () => import("@/views/Components/Descriptions.vue"),
			meta: { title: "Components Descriptions" }
		},
		{
			path: "empty",
			name: "Components-Empty",
			component: () => import("@/views/Components/Empty.vue"),
			meta: { title: "Components Empty" }
		},
		{
			path: "image",
			name: "Components-Image",
			component: () => import("@/views/Components/Image.vue"),
			meta: { title: "Components Image" }
		},
		{
			path: "list",
			name: "Components-List",
			component: () => import("@/views/Components/List.vue"),
			meta: { title: "Components List" }
		},
		{
			path: "numberanimation",
			name: "Components-NumberAnimation",
			component: () => import("@/views/Components/NumberAnimation.vue"),
			meta: { title: "Components Number Animation" }
		},
		{
			path: "scrollbar",
			name: "Components-Scrollbar",
			component: () => import("@/views/Components/Scrollbar.vue"),
			meta: { title: "Components Scrollbar" }
		},
		{
			path: "statistic",
			name: "Components-Statistic",
			component: () => import("@/views/Components/Statistic.vue"),
			meta: { title: "Components Statistic" }
		},
		{
			path: "table",
			name: "Components-Table",
			component: () => import("@/views/Components/Table.vue"),
			meta: { title: "Components Table" }
		},
		{
			path: "thing",
			name: "Components-Thing",
			component: () => import("@/views/Components/Thing.vue"),
			meta: { title: "Components Thing" }
		},
		{
			path: "time",
			name: "Components-Time",
			component: () => import("@/views/Components/Time.vue"),
			meta: { title: "Components Time" }
		},
		{
			path: "timeline",
			name: "Components-Timeline",
			component: () => import("@/views/Components/Timeline.vue"),
			meta: { title: "Components Timeline" }
		},
		{
			path: "tree",
			name: "Components-Tree",
			component: () => import("@/views/Components/Tree.vue"),
			meta: { title: "Components Tree" }
		},
		{
			path: "affix",
			name: "Components-Affix",
			component: () => import("@/views/Components/Affix.vue"),
			meta: { title: "Components Affix" }
		},
		{
			path: "anchor",
			name: "Components-Anchor",
			component: () => import("@/views/Components/Anchor.vue"),
			meta: { title: "Components Anchor" }
		},
		{
			path: "backtop",
			name: "Components-BackTop",
			component: () => import("@/views/Components/BackTop.vue"),
			meta: { title: "Components Back Top" }
		},
		{
			path: "breadcrumb",
			name: "Components-Breadcrumb",
			component: () => import("@/views/Components/Breadcrumb.vue"),
			meta: { title: "Components Breadcrumb" }
		},
		{
			path: "menu",
			name: "Components-Menu",
			component: () => import("@/views/Components/Menu.vue"),
			meta: { title: "Components Menu" }
		},
		{
			path: "pagination",
			name: "Components-Pagination",
			component: () => import("@/views/Components/Pagination.vue"),
			meta: { title: "Components Pagination" }
		},
		{
			path: "steps",
			name: "Components-Steps",
			component: () => import("@/views/Components/Steps.vue"),
			meta: { title: "Components Steps" }
		},
		{
			path: "tabs",
			name: "Components-Tabs",
			component: () => import("@/views/Components/Tabs.vue"),
			meta: { title: "Components Tabs" }
		},
		{
			path: "alert",
			name: "Components-Alert",
			component: () => import("@/views/Components/Alert.vue"),
			meta: { title: "Components Alert" }
		},
		{
			path: "badge",
			name: "Components-Badge",
			component: () => import("@/views/Components/Badge.vue"),
			meta: { title: "Components Badge" }
		},
		{
			path: "dialog",
			name: "Components-Dialog",
			component: () => import("@/views/Components/Dialog.vue"),
			meta: { title: "Components Dialog" }
		},
		{
			path: "drawer",
			name: "Components-Drawer",
			component: () => import("@/views/Components/Drawer.vue"),
			meta: { title: "Components Drawer" }
		},
		{
			path: "message",
			name: "Components-Message",
			component: () => import("@/views/Components/Message.vue"),
			meta: { title: "Components Message" }
		},
		{
			path: "modal",
			name: "Components-Modal",
			component: () => import("@/views/Components/Modal.vue"),
			meta: { title: "Components Modal" }
		},
		{
			path: "notification",
			name: "Components-Notification",
			component: () => import("@/views/Components/Notification.vue"),
			meta: { title: "Components Notification" }
		},
		{
			path: "popconfirm",
			name: "Components-Popconfirm",
			component: () => import("@/views/Components/Popconfirm.vue"),
			meta: { title: "Components Popconfirm" }
		},
		{
			path: "popover",
			name: "Components-Popover",
			component: () => import("@/views/Components/Popover.vue"),
			meta: { title: "Components Popover" }
		},
		{
			path: "popselect",
			name: "Components-Popselect",
			component: () => import("@/views/Components/Popselect.vue"),
			meta: { title: "Components Popselect" }
		},
		{
			path: "progress",
			name: "Components-Progress",
			component: () => import("@/views/Components/Progress.vue"),
			meta: { title: "Components Progress" }
		},
		{
			path: "result",
			name: "Components-Result",
			component: () => import("@/views/Components/Result.vue"),
			meta: { title: "Components Result" }
		},
		{
			path: "skeleton",
			name: "Components-Skeleton",
			component: () => import("@/views/Components/Skeleton.vue"),
			meta: { title: "Components Skeleton" }
		},
		{
			path: "spin",
			name: "Components-Spin",
			component: () => import("@/views/Components/Spin.vue"),
			meta: { title: "Components Spin" }
		},
		{
			path: "tooltip",
			name: "Components-Tooltip",
			component: () => import("@/views/Components/Tooltip.vue"),
			meta: { title: "Components Tooltip" }
		},
		{
			path: "layout",
			name: "Components-Layout",
			component: () => import("@/views/Components/Layout.vue"),
			meta: { title: "Components Layout" }
		},
		{
			path: "legacygrid",
			name: "Components-LegacyGrid",
			component: () => import("@/views/Components/LegacyGrid.vue"),
			meta: { title: "Components Legacy Grid" }
		},
		{
			path: "grid",
			name: "Components-Grid",
			component: () => import("@/views/Components/Grid.vue"),
			meta: { title: "Components Grid" }
		},
		{
			path: "space",
			name: "Components-Space",
			component: () => import("@/views/Components/Space.vue"),
			meta: { title: "Components Space" }
		}
	]
}
