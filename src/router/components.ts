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
			name: "components-avatar",
			component: () => import("@/views/Components/Avatar.vue"),
			meta: { title: "Components Avatar" }
		},
		{
			path: "button",
			name: "components-button",
			component: () => import("@/views/Components/Button.vue"),
			meta: { title: "Components Button" }
		},
		{
			path: "card",
			name: "components-card",
			component: () => import("@/views/Components/Card.vue"),
			meta: { title: "Components Card" }
		},
		{
			path: "carousel",
			name: "components-carousel",
			component: () => import("@/views/Components/Carousel.vue"),
			meta: { title: "Components Carousel" }
		},
		{
			path: "collapse",
			name: "components-collapse",
			component: () => import("@/views/Components/Collapse.vue"),
			meta: { title: "Components Collapse" }
		},
		{
			path: "divider",
			name: "components-divider",
			component: () => import("@/views/Components/Divider.vue"),
			meta: { title: "Components Divider" }
		},
		{
			path: "dropdown",
			name: "components-dropdown",
			component: () => import("@/views/Components/Dropdown.vue"),
			meta: { title: "Components Dropdown" }
		},
		{
			path: "ellipsis",
			name: "components-ellipsis",
			component: () => import("@/views/Components/Ellipsis.vue"),
			meta: { title: "Components Ellipsis" }
		},
		{
			path: "gradient-text",
			name: "components-gradient-text",
			component: () => import("@/views/Components/GradientText.vue"),
			meta: { title: "Components Gradient Text" }
		},
		{
			path: "icon",
			name: "components-icon",
			component: () => import("@/views/Components/Icon.vue"),
			meta: { title: "Components Icon" }
		},
		{
			path: "page-header",
			name: "components-page-header",
			component: () => import("@/views/Components/PageHeader.vue"),
			meta: { title: "Components Page Header" }
		},
		{
			path: "tag",
			name: "components-tag",
			component: () => import("@/views/Components/Tag.vue"),
			meta: { title: "Components Tag" }
		},
		{
			path: "typography",
			name: "components-typography",
			component: () => import("@/views/Components/Typography.vue"),
			meta: { title: "Components Typography" }
		},
		{
			path: "watermark",
			name: "components-watermark",
			component: () => import("@/views/Components/Watermark.vue"),
			meta: { title: "Components Watermark" }
		},
		{
			path: "auto-complete",
			name: "components-auto-complete",
			component: () => import("@/views/Components/AutoComplete.vue"),
			meta: { title: "Components Auto Complete" }
		},
		{
			path: "cascader",
			name: "components-cascader",
			component: () => import("@/views/Components/Cascader.vue"),
			meta: { title: "Components Cascader" }
		},
		{
			path: "color-picker",
			name: "components-color-picker",
			component: () => import("@/views/Components/ColorPicker.vue"),
			meta: { title: "Components Color Picker" }
		},
		{
			path: "checkbox",
			name: "components-checkbox",
			component: () => import("@/views/Components/Checkbox.vue"),
			meta: { title: "Components Checkbox" }
		},
		{
			path: "date-picker",
			name: "components-date-picker",
			component: () => import("@/views/Components/DatePicker.vue"),
			meta: { title: "Components Date Picker" }
		},
		{
			path: "dynamic-input",
			name: "components-dynamic-input",
			component: () => import("@/views/Components/DynamicInput.vue"),
			meta: { title: "Components Dynamic Input" }
		},
		{
			path: "dynamic-tags",
			name: "components-dynamic-tags",
			component: () => import("@/views/Components/DynamicTags.vue"),
			meta: { title: "Components Dynamic Tags" }
		},
		{
			path: "form",
			name: "components-form",
			component: () => import("@/views/Components/Form.vue"),
			meta: { title: "Components Form" }
		},
		{
			path: "input",
			name: "components-input",
			component: () => import("@/views/Components/Input.vue"),
			meta: { title: "Components Input" }
		},
		{
			path: "input-number",
			name: "components-input-number",
			component: () => import("@/views/Components/InputNumber.vue"),
			meta: { title: "Components Input Number" }
		},
		{
			path: "mention",
			name: "components-mention",
			component: () => import("@/views/Components/Mention.vue"),
			meta: { title: "Components Mention" }
		},
		{
			path: "radio",
			name: "components-radio",
			component: () => import("@/views/Components/Radio.vue"),
			meta: { title: "Components Radio" }
		},
		{
			path: "rate",
			name: "components-rate",
			component: () => import("@/views/Components/Rate.vue"),
			meta: { title: "Components Rate" }
		},
		{
			path: "select",
			name: "components-select",
			component: () => import("@/views/Components/Select.vue"),
			meta: { title: "Components Select" }
		},
		{
			path: "slider",
			name: "components-slider",
			component: () => import("@/views/Components/Slider.vue"),
			meta: { title: "Components Slider" }
		},
		{
			path: "switch",
			name: "components-switch",
			component: () => import("@/views/Components/Switch.vue"),
			meta: { title: "Components Switch" }
		},
		{
			path: "time-picker",
			name: "components-time-picker",
			component: () => import("@/views/Components/TimePicker.vue"),
			meta: { title: "Components Time Picker" }
		},
		{
			path: "transfer",
			name: "components-transfer",
			component: () => import("@/views/Components/Transfer.vue"),
			meta: { title: "Components Transfer" }
		},
		{
			path: "tree-select",
			name: "components-tree-select",
			component: () => import("@/views/Components/TreeSelect.vue"),
			meta: { title: "Components Tree Select" }
		},
		{
			path: "upload",
			name: "components-upload",
			component: () => import("@/views/Components/Upload.vue"),
			meta: { title: "Components Upload" }
		},
		{
			path: "calendar",
			name: "components-calendar",
			component: () => import("@/views/Components/Calendar.vue"),
			meta: { title: "Components Calendar" }
		},
		{
			path: "countdown",
			name: "components-countdown",
			component: () => import("@/views/Components/Countdown.vue"),
			meta: { title: "Components Countdown" }
		},
		{
			path: "data-table",
			name: "components-data-table",
			component: () => import("@/views/Components/DataTable.vue"),
			meta: { title: "Components Data Table" }
		},
		{
			path: "descriptions",
			name: "components-descriptions",
			component: () => import("@/views/Components/Descriptions.vue"),
			meta: { title: "Components Descriptions" }
		},
		{
			path: "empty",
			name: "components-empty",
			component: () => import("@/views/Components/Empty.vue"),
			meta: { title: "Components Empty" }
		},
		{
			path: "image",
			name: "components-image",
			component: () => import("@/views/Components/Image.vue"),
			meta: { title: "Components Image" }
		},
		{
			path: "list",
			name: "components-list",
			component: () => import("@/views/Components/List.vue"),
			meta: { title: "Components List" }
		},
		{
			path: "number-animation",
			name: "components-number-animation",
			component: () => import("@/views/Components/NumberAnimation.vue"),
			meta: { title: "Components Number Animation" }
		},
		{
			path: "scrollbar",
			name: "components-scrollbar",
			component: () => import("@/views/Components/Scrollbar.vue"),
			meta: { title: "Components Scrollbar" }
		},
		{
			path: "statistic",
			name: "components-statistic",
			component: () => import("@/views/Components/Statistic.vue"),
			meta: { title: "Components Statistic" }
		},
		{
			path: "table",
			name: "components-table",
			component: () => import("@/views/Components/Table.vue"),
			meta: { title: "Components Table" }
		},
		{
			path: "thing",
			name: "components-thing",
			component: () => import("@/views/Components/Thing.vue"),
			meta: { title: "Components Thing" }
		},
		{
			path: "time",
			name: "components-time",
			component: () => import("@/views/Components/Time.vue"),
			meta: { title: "Components Time" }
		},
		{
			path: "timeline",
			name: "components-timeline",
			component: () => import("@/views/Components/Timeline.vue"),
			meta: { title: "Components Timeline" }
		},
		{
			path: "tree",
			name: "components-tree",
			component: () => import("@/views/Components/Tree.vue"),
			meta: { title: "Components Tree" }
		},
		{
			path: "affix",
			name: "components-affix",
			component: () => import("@/views/Components/Affix.vue"),
			meta: { title: "Components Affix" }
		},
		{
			path: "anchor",
			name: "components-anchor",
			component: () => import("@/views/Components/Anchor.vue"),
			meta: { title: "Components Anchor" }
		},
		{
			path: "back-top",
			name: "components-back-top",
			component: () => import("@/views/Components/BackTop.vue"),
			meta: { title: "Components Back Top" }
		},
		{
			path: "breadcrumb",
			name: "components-breadcrumb",
			component: () => import("@/views/Components/Breadcrumb.vue"),
			meta: { title: "Components Breadcrumb" }
		},
		{
			path: "menu",
			name: "components-menu",
			component: () => import("@/views/Components/Menu.vue"),
			meta: { title: "Components Menu" }
		},
		{
			path: "pagination",
			name: "components-pagination",
			component: () => import("@/views/Components/Pagination.vue"),
			meta: { title: "Components Pagination" }
		},
		{
			path: "steps",
			name: "components-steps",
			component: () => import("@/views/Components/Steps.vue"),
			meta: { title: "Components Steps" }
		},
		{
			path: "tabs",
			name: "components-tabs",
			component: () => import("@/views/Components/Tabs.vue"),
			meta: { title: "Components Tabs" }
		},
		{
			path: "alert",
			name: "components-alert",
			component: () => import("@/views/Components/Alert.vue"),
			meta: { title: "Components Alert" }
		},
		{
			path: "badge",
			name: "components-badge",
			component: () => import("@/views/Components/Badge.vue"),
			meta: { title: "Components Badge" }
		},
		{
			path: "dialog",
			name: "components-dialog",
			component: () => import("@/views/Components/Dialog.vue"),
			meta: { title: "Components Dialog" }
		},
		{
			path: "drawer",
			name: "components-drawer",
			component: () => import("@/views/Components/Drawer.vue"),
			meta: { title: "Components Drawer" }
		},
		{
			path: "message",
			name: "components-message",
			component: () => import("@/views/Components/Message.vue"),
			meta: { title: "Components Message" }
		},
		{
			path: "modal",
			name: "components-modal",
			component: () => import("@/views/Components/Modal.vue"),
			meta: { title: "Components Modal" }
		},
		{
			path: "notification",
			name: "components-notification",
			component: () => import("@/views/Components/Notification.vue"),
			meta: { title: "Components Notification" }
		},
		{
			path: "popconfirm",
			name: "components-popconfirm",
			component: () => import("@/views/Components/Popconfirm.vue"),
			meta: { title: "Components Popconfirm" }
		},
		{
			path: "popover",
			name: "components-popover",
			component: () => import("@/views/Components/Popover.vue"),
			meta: { title: "Components Popover" }
		},
		{
			path: "popselect",
			name: "components-popselect",
			component: () => import("@/views/Components/Popselect.vue"),
			meta: { title: "Components Popselect" }
		},
		{
			path: "progress",
			name: "components-progress",
			component: () => import("@/views/Components/Progress.vue"),
			meta: { title: "Components Progress" }
		},
		{
			path: "result",
			name: "components-result",
			component: () => import("@/views/Components/Result.vue"),
			meta: { title: "Components Result" }
		},
		{
			path: "skeleton",
			name: "components-skeleton",
			component: () => import("@/views/Components/Skeleton.vue"),
			meta: { title: "Components Skeleton" }
		},
		{
			path: "spin",
			name: "components-spin",
			component: () => import("@/views/Components/Spin.vue"),
			meta: { title: "Components Spin" }
		},
		{
			path: "tooltip",
			name: "components-tooltip",
			component: () => import("@/views/Components/Tooltip.vue"),
			meta: { title: "Components Tooltip" }
		},
		{
			path: "layout",
			name: "components-layout",
			component: () => import("@/views/Components/Layout.vue"),
			meta: { title: "Components Layout" }
		},
		{
			path: "legacy-grid",
			name: "components-legacy-grid",
			component: () => import("@/views/Components/LegacyGrid.vue"),
			meta: { title: "Components Legacy Grid" }
		},
		{
			path: "grid",
			name: "components-grid",
			component: () => import("@/views/Components/Grid.vue"),
			meta: { title: "Components Grid" }
		},
		{
			path: "space",
			name: "components-space",
			component: () => import("@/views/Components/Space.vue"),
			meta: { title: "Components Space" }
		}
	]
}
