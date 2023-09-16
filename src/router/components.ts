import ComponentsIcon from "@vicons/fluent/Apps24Regular"

export default {
	path: "/components",
	redirect: "/components/avatar",
	meta: {
		auth: true,
		roles: "all"
	},
	children: [
		{
			path: "avatar",
			name: "components-avatar",
			component: () => import("@/views/Components/Avatar.vue"),
			meta: { icon: ComponentsIcon, title: "Components Avatar" }
		},
		{
			path: "button",
			name: "components-button",
			component: () => import("@/views/Components/Button.vue"),
			meta: { icon: ComponentsIcon, title: "Components Button" }
		},
		{
			path: "card",
			name: "components-card",
			component: () => import("@/views/Components/Card.vue"),
			meta: { icon: ComponentsIcon, title: "Components Card" }
		},
		{
			path: "carousel",
			name: "components-carousel",
			component: () => import("@/views/Components/Carousel.vue"),
			meta: { icon: ComponentsIcon, title: "Components Carousel" }
		},
		{
			path: "collapse",
			name: "components-collapse",
			component: () => import("@/views/Components/Collapse.vue"),
			meta: { icon: ComponentsIcon, title: "Components Collapse" }
		},
		{
			path: "divider",
			name: "components-divider",
			component: () => import("@/views/Components/Divider.vue"),
			meta: { icon: ComponentsIcon, title: "Components Divider" }
		},
		{
			path: "dropdown",
			name: "components-dropdown",
			component: () => import("@/views/Components/Dropdown.vue"),
			meta: { icon: ComponentsIcon, title: "Components Dropdown" }
		},
		{
			path: "ellipsis",
			name: "components-ellipsis",
			component: () => import("@/views/Components/Ellipsis.vue"),
			meta: { icon: ComponentsIcon, title: "Components Ellipsis" }
		},
		{
			path: "gradient-text",
			name: "components-gradient-text",
			component: () => import("@/views/Components/GradientText.vue"),
			meta: { icon: ComponentsIcon, title: "Components Gradient Text" }
		},
		{
			path: "icon",
			name: "components-icon",
			component: () => import("@/views/Components/Icon.vue"),
			meta: { icon: ComponentsIcon, title: "Components Icon" }
		},
		{
			path: "page-header",
			name: "components-page-header",
			component: () => import("@/views/Components/PageHeader.vue"),
			meta: { icon: ComponentsIcon, title: "Components Page Header" }
		},
		{
			path: "tag",
			name: "components-tag",
			component: () => import("@/views/Components/Tag.vue"),
			meta: { icon: ComponentsIcon, title: "Components Tag" }
		},
		{
			path: "typography",
			name: "components-typography",
			component: () => import("@/views/Components/Typography.vue"),
			meta: { icon: ComponentsIcon, title: "Components Typography" }
		},
		{
			path: "watermark",
			name: "components-watermark",
			component: () => import("@/views/Components/Watermark.vue"),
			meta: { icon: ComponentsIcon, title: "Components Watermark" }
		},
		{
			path: "auto-complete",
			name: "components-auto-complete",
			component: () => import("@/views/Components/AutoComplete.vue"),
			meta: { icon: ComponentsIcon, title: "Components Auto Complete" }
		},
		{
			path: "cascader",
			name: "components-cascader",
			component: () => import("@/views/Components/Cascader.vue"),
			meta: { icon: ComponentsIcon, title: "Components Cascader" }
		},
		{
			path: "color-picker",
			name: "components-color-picker",
			component: () => import("@/views/Components/ColorPicker.vue"),
			meta: { icon: ComponentsIcon, title: "Components Color Picker" }
		},
		{
			path: "checkbox",
			name: "components-checkbox",
			component: () => import("@/views/Components/Checkbox.vue"),
			meta: { icon: ComponentsIcon, title: "Components Checkbox" }
		},
		{
			path: "date-picker",
			name: "components-date-picker",
			component: () => import("@/views/Components/DatePicker.vue"),
			meta: { icon: ComponentsIcon, title: "Components Date Picker" }
		},
		{
			path: "dynamic-input",
			name: "components-dynamic-input",
			component: () => import("@/views/Components/DynamicInput.vue"),
			meta: { icon: ComponentsIcon, title: "Components Dynamic Input" }
		},
		{
			path: "dynamic-tags",
			name: "components-dynamic-tags",
			component: () => import("@/views/Components/DynamicTags.vue"),
			meta: { icon: ComponentsIcon, title: "Components Dynamic Tags" }
		},
		{
			path: "form",
			name: "components-form",
			component: () => import("@/views/Components/Form.vue"),
			meta: { icon: ComponentsIcon, title: "Components Form" }
		},
		{
			path: "input",
			name: "components-input",
			component: () => import("@/views/Components/Input.vue"),
			meta: { icon: ComponentsIcon, title: "Components Input" }
		},
		{
			path: "input-number",
			name: "components-input-number",
			component: () => import("@/views/Components/InputNumber.vue"),
			meta: { icon: ComponentsIcon, title: "Components Input Number" }
		},
		{
			path: "mention",
			name: "components-mention",
			component: () => import("@/views/Components/Mention.vue"),
			meta: { icon: ComponentsIcon, title: "Components Mention" }
		},
		{
			path: "radio",
			name: "components-radio",
			component: () => import("@/views/Components/Radio.vue"),
			meta: { icon: ComponentsIcon, title: "Components Radio" }
		},
		{
			path: "rate",
			name: "components-rate",
			component: () => import("@/views/Components/Rate.vue"),
			meta: { icon: ComponentsIcon, title: "Components Rate" }
		},
		{
			path: "select",
			name: "components-select",
			component: () => import("@/views/Components/Select.vue"),
			meta: { icon: ComponentsIcon, title: "Components Select" }
		},
		{
			path: "slider",
			name: "components-slider",
			component: () => import("@/views/Components/Slider.vue"),
			meta: { icon: ComponentsIcon, title: "Components Slider" }
		},
		{
			path: "switch",
			name: "components-switch",
			component: () => import("@/views/Components/Switch.vue"),
			meta: { icon: ComponentsIcon, title: "Components Switch" }
		},
		{
			path: "time-picker",
			name: "components-time-picker",
			component: () => import("@/views/Components/TimePicker.vue"),
			meta: { icon: ComponentsIcon, title: "Components Time Picker" }
		},
		{
			path: "transfer",
			name: "components-transfer",
			component: () => import("@/views/Components/Transfer.vue"),
			meta: { icon: ComponentsIcon, title: "Components Transfer" }
		},
		{
			path: "tree-select",
			name: "components-tree-select",
			component: () => import("@/views/Components/TreeSelect.vue"),
			meta: { icon: ComponentsIcon, title: "Components Tree Select" }
		},
		{
			path: "upload",
			name: "components-upload",
			component: () => import("@/views/Components/Upload.vue"),
			meta: { icon: ComponentsIcon, title: "Components Upload" }
		},
		{
			path: "calendar",
			name: "components-calendar",
			component: () => import("@/views/Components/Calendar.vue"),
			meta: { icon: ComponentsIcon, title: "Components Calendar" }
		},
		{
			path: "countdown",
			name: "components-countdown",
			component: () => import("@/views/Components/Countdown.vue"),
			meta: { icon: ComponentsIcon, title: "Components Countdown" }
		},
		{
			path: "data-table",
			name: "components-data-table",
			component: () => import("@/views/Components/DataTable.vue"),
			meta: { icon: ComponentsIcon, title: "Components Data Table" }
		},
		{
			path: "descriptions",
			name: "components-descriptions",
			component: () => import("@/views/Components/Descriptions.vue"),
			meta: { icon: ComponentsIcon, title: "Components Descriptions" }
		},
		{
			path: "empty",
			name: "components-empty",
			component: () => import("@/views/Components/Empty.vue"),
			meta: { icon: ComponentsIcon, title: "Components Empty" }
		},
		{
			path: "image",
			name: "components-image",
			component: () => import("@/views/Components/Image.vue"),
			meta: { icon: ComponentsIcon, title: "Components Image" }
		},
		{
			path: "list",
			name: "components-list",
			component: () => import("@/views/Components/List.vue"),
			meta: { icon: ComponentsIcon, title: "Components List" }
		},
		{
			path: "number-animation",
			name: "components-number-animation",
			component: () => import("@/views/Components/NumberAnimation.vue"),
			meta: { icon: ComponentsIcon, title: "Components Number Animation" }
		},
		{
			path: "scrollbar",
			name: "components-scrollbar",
			component: () => import("@/views/Components/Scrollbar.vue"),
			meta: { icon: ComponentsIcon, title: "Components Scrollbar" }
		},
		{
			path: "statistic",
			name: "components-statistic",
			component: () => import("@/views/Components/Statistic.vue"),
			meta: { icon: ComponentsIcon, title: "Components Statistic" }
		},
		{
			path: "table",
			name: "components-table",
			component: () => import("@/views/Components/Table.vue"),
			meta: { icon: ComponentsIcon, title: "Components Table" }
		},
		{
			path: "thing",
			name: "components-thing",
			component: () => import("@/views/Components/Thing.vue"),
			meta: { icon: ComponentsIcon, title: "Components Thing" }
		},
		{
			path: "time",
			name: "components-time",
			component: () => import("@/views/Components/Time.vue"),
			meta: { icon: ComponentsIcon, title: "Components Time" }
		},
		{
			path: "timeline",
			name: "components-timeline",
			component: () => import("@/views/Components/Timeline.vue"),
			meta: { icon: ComponentsIcon, title: "Components Timeline" }
		},
		{
			path: "tree",
			name: "components-tree",
			component: () => import("@/views/Components/Tree.vue"),
			meta: { icon: ComponentsIcon, title: "Components Tree" }
		},
		{
			path: "affix",
			name: "components-affix",
			component: () => import("@/views/Components/Affix.vue"),
			meta: { icon: ComponentsIcon, title: "Components Affix" }
		},
		{
			path: "anchor",
			name: "components-anchor",
			component: () => import("@/views/Components/Anchor.vue"),
			meta: { icon: ComponentsIcon, title: "Components Anchor" }
		},
		{
			path: "back-top",
			name: "components-back-top",
			component: () => import("@/views/Components/BackTop.vue"),
			meta: { icon: ComponentsIcon, title: "Components Back Top" }
		},
		{
			path: "breadcrumb",
			name: "components-breadcrumb",
			component: () => import("@/views/Components/Breadcrumb.vue"),
			meta: { icon: ComponentsIcon, title: "Components Breadcrumb" }
		},
		{
			path: "menu",
			name: "components-menu",
			component: () => import("@/views/Components/Menu.vue"),
			meta: { icon: ComponentsIcon, title: "Components Menu" }
		},
		{
			path: "pagination",
			name: "components-pagination",
			component: () => import("@/views/Components/Pagination.vue"),
			meta: { icon: ComponentsIcon, title: "Components Pagination" }
		},
		{
			path: "steps",
			name: "components-steps",
			component: () => import("@/views/Components/Steps.vue"),
			meta: { icon: ComponentsIcon, title: "Components Steps" }
		},
		{
			path: "tabs",
			name: "components-tabs",
			component: () => import("@/views/Components/Tabs.vue"),
			meta: { icon: ComponentsIcon, title: "Components Tabs" }
		},
		{
			path: "alert",
			name: "components-alert",
			component: () => import("@/views/Components/Alert.vue"),
			meta: { icon: ComponentsIcon, title: "Components Alert" }
		},
		{
			path: "badge",
			name: "components-badge",
			component: () => import("@/views/Components/Badge.vue"),
			meta: { icon: ComponentsIcon, title: "Components Badge" }
		},
		{
			path: "dialog",
			name: "components-dialog",
			component: () => import("@/views/Components/Dialog.vue"),
			meta: { icon: ComponentsIcon, title: "Components Dialog" }
		},
		{
			path: "drawer",
			name: "components-drawer",
			component: () => import("@/views/Components/Drawer.vue"),
			meta: { icon: ComponentsIcon, title: "Components Drawer" }
		},
		{
			path: "message",
			name: "components-message",
			component: () => import("@/views/Components/Message.vue"),
			meta: { icon: ComponentsIcon, title: "Components Message" }
		},
		{
			path: "modal",
			name: "components-modal",
			component: () => import("@/views/Components/Modal.vue"),
			meta: { icon: ComponentsIcon, title: "Components Modal" }
		},
		{
			path: "notification",
			name: "components-notification",
			component: () => import("@/views/Components/Notification.vue"),
			meta: { icon: ComponentsIcon, title: "Components Notification" }
		},
		{
			path: "popconfirm",
			name: "components-popconfirm",
			component: () => import("@/views/Components/Popconfirm.vue"),
			meta: { icon: ComponentsIcon, title: "Components Popconfirm" }
		},
		{
			path: "popover",
			name: "components-popover",
			component: () => import("@/views/Components/Popover.vue"),
			meta: { icon: ComponentsIcon, title: "Components Popover" }
		},
		{
			path: "popselect",
			name: "components-popselect",
			component: () => import("@/views/Components/Popselect.vue"),
			meta: { icon: ComponentsIcon, title: "Components Popselect" }
		},
		{
			path: "progress",
			name: "components-progress",
			component: () => import("@/views/Components/Progress.vue"),
			meta: { icon: ComponentsIcon, title: "Components Progress" }
		},
		{
			path: "result",
			name: "components-result",
			component: () => import("@/views/Components/Result.vue"),
			meta: { icon: ComponentsIcon, title: "Components Result" }
		},
		{
			path: "skeleton",
			name: "components-skeleton",
			component: () => import("@/views/Components/Skeleton.vue"),
			meta: { icon: ComponentsIcon, title: "Components Skeleton" }
		},
		{
			path: "spin",
			name: "components-spin",
			component: () => import("@/views/Components/Spin.vue"),
			meta: { icon: ComponentsIcon, title: "Components Spin" }
		},
		{
			path: "tooltip",
			name: "components-tooltip",
			component: () => import("@/views/Components/Tooltip.vue"),
			meta: { icon: ComponentsIcon, title: "Components Tooltip" }
		},
		{
			path: "layout",
			name: "components-layout",
			component: () => import("@/views/Components/Layout.vue"),
			meta: { icon: ComponentsIcon, title: "Components Layout" }
		},
		{
			path: "legacy-grid",
			name: "components-legacy-grid",
			component: () => import("@/views/Components/LegacyGrid.vue"),
			meta: { icon: ComponentsIcon, title: "Components Legacy Grid" }
		},
		{
			path: "grid",
			name: "components-grid",
			component: () => import("@/views/Components/Grid.vue"),
			meta: { icon: ComponentsIcon, title: "Components Grid" }
		},
		{
			path: "space",
			name: "components-space",
			component: () => import("@/views/Components/Space.vue"),
			meta: { icon: ComponentsIcon, title: "Components Space" }
		}
	]
}
