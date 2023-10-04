import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import ComponentsIcon from "@vicons/fluent/Apps24Regular"
import { type MenuMixedOption } from "naive-ui/es/menu/src/interface"

const components = [
	{
		key: "components-group-common",
		label: "Common",
		items: [
			{ key: "components-avatar", label: "Avatar" },
			{ key: "components-button", label: "Button" },
			{ key: "components-card", label: "Card" },
			{ key: "components-carousel", label: "Carousel" },
			{ key: "components-collapse", label: "Collapse" },
			{ key: "components-divider", label: "Divider" },
			{ key: "components-dropdown", label: "Dropdown" },
			{ key: "components-ellipsis", label: "Ellipsis" },
			{ key: "components-gradient-text", label: "Gradient Text" },
			{ key: "components-icon", label: "Icon" },
			{ key: "components-page-header", label: "Page Header" },
			{ key: "components-tag", label: "Tag" },
			{ key: "components-typography", label: "Typography" },
			{ key: "components-watermark", label: "Watermark" }
		]
	},
	{
		key: "components-group-input",
		label: "Input",
		items: [
			{ key: "components-auto-complete", label: "Auto Complete" },
			{ key: "components-cascader", label: "Cascader" },
			{ key: "components-color-picker", label: "Color Picker" },
			{ key: "components-checkbox", label: "Checkbox" },
			{ key: "components-date-picker", label: "Date Picker" },
			{ key: "components-dynamic-input", label: "Dynamic Input" },
			{ key: "components-dynamic-tags", label: "Dynamic Tags" },
			{ key: "components-form", label: "Form" },
			{ key: "components-input", label: "Input" },
			{ key: "components-input-number", label: "Input Number" },
			{ key: "components-mention", label: "Mention" },
			{ key: "components-radio", label: "Radio" },
			{ key: "components-rate", label: "Rate" },
			{ key: "components-select", label: "Select" },
			{ key: "components-slider", label: "Slider" },
			{ key: "components-switch", label: "Switch" },
			{ key: "components-time-picker", label: "Time Picker" },
			{ key: "components-transfer", label: "Transfer" },
			{ key: "components-tree-select", label: "Tree Select" },
			{ key: "components-upload", label: "Upload" }
		]
	},
	{
		key: "components-group-data-display",
		label: "Data Display",
		items: [
			{ key: "components-calendar", label: "Calendar" },
			{ key: "components-countdown", label: "Countdown" },
			{ key: "components-data-table", label: "Data Table" },
			{ key: "components-descriptions", label: "Descriptions" },
			{ key: "components-empty", label: "Empty" },
			{ key: "components-image", label: "Image" },
			{ key: "components-list", label: "List" },
			{ key: "components-number-animation", label: "Number Animation" },
			{ key: "components-scrollbar", label: "Scrollbar" },
			{ key: "components-statistic", label: "Statistic" },
			{ key: "components-table", label: "Table" },
			{ key: "components-thing", label: "Thing" },
			{ key: "components-time", label: "Time" },
			{ key: "components-timeline", label: "Timeline" },
			{ key: "components-tree", label: "Tree" }
		]
	},
	{
		key: "components-group-navigation",
		label: "Navigation",
		items: [
			{ key: "components-affix", label: "Affix" },
			{ key: "components-anchor", label: "Anchor" },
			{ key: "components-back-top", label: "Back Top" },
			{ key: "components-breadcrumb", label: "Breadcrumb" },
			{ key: "components-menu", label: "Menu" },
			{ key: "components-pagination", label: "Pagination" },
			{ key: "components-steps", label: "Steps" },
			{ key: "components-tabs", label: "Tabs" }
		]
	},
	{
		key: "components-group-feedback",
		label: "Feedback",
		items: [
			{ key: "components-alert", label: "Alert" },
			{ key: "components-badge", label: "Badge" },
			{ key: "components-dialog", label: "Dialog" },
			{ key: "components-drawer", label: "Drawer" },
			{ key: "components-message", label: "Message" },
			{ key: "components-modal", label: "Modal" },
			{ key: "components-notification", label: "Notification" },
			{ key: "components-popconfirm", label: "Popconfirm" },
			{ key: "components-popover", label: "Popover" },
			{ key: "components-popselect", label: "Popselect" },
			{ key: "components-progress", label: "Progress" },
			{ key: "components-result", label: "Result" },
			{ key: "components-skeleton", label: "Skeleton" },
			{ key: "components-spin", label: "Spin" },
			{ key: "components-tooltip", label: "Tooltip" }
		]
	},
	{
		key: "components-group-layout",
		label: "Layout",
		items: [
			{ key: "components-layout", label: "Layout" },
			{ key: "components-legacy-grid", label: "Legacy Grid" },
			{ key: "components-grid", label: "Grid" },
			{ key: "components-space", label: "Space" }
		]
	}
]

const tot = components.reduce((pre, cur) => {
	return pre + cur.items.length
}, 0)

export default function getItems(): MenuMixedOption {
	return {
		label: () => (
			<div class={"item-badge"}>
				<div>Components</div>
				<div>{tot}</div>
			</div>
		),
		key: "components",
		icon: renderIcon(ComponentsIcon),
		children: components.map(({ key, label, items }) => ({
			label: () => (
				<div class={"item-badge"}>
					<div>{label}</div>
					<div>{items.length}</div>
				</div>
			),
			key,
			children: items.map(({ key, label }) => ({
				key,
				label: () =>
					h(
						RouterLink,
						{
							to: {
								name: key
							}
						},
						{ default: () => label }
					)
			}))
		}))
	}
}
