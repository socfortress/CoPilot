import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const ComponentsIcon = "fluent:apps-24-regular"
import { type MenuMixedOption } from "naive-ui/es/menu/src/interface"

const components = [
	{
		key: "Components-Group-common",
		label: "Common",
		items: [
			{ key: "Components-Avatar", label: "Avatar" },
			{ key: "Components-Button", label: "Button" },
			{ key: "Components-Card", label: "Card" },
			{ key: "Components-Carousel", label: "Carousel" },
			{ key: "Components-Collapse", label: "Collapse" },
			{ key: "Components-Divider", label: "Divider" },
			{ key: "Components-Dropdown", label: "Dropdown" },
			{ key: "Components-Ellipsis", label: "Ellipsis" },
			{ key: "Components-GradientText", label: "Gradient Text" },
			{ key: "Components-Icon", label: "Icon" },
			{ key: "Components-PageHeader", label: "Page Header" },
			{ key: "Components-Tag", label: "Tag" },
			{ key: "Components-Typography", label: "Typography" },
			{ key: "Components-Watermark", label: "Watermark" }
		]
	},
	{
		key: "Components-Group-input",
		label: "Input",
		items: [
			{ key: "Components-AutoComplete", label: "Auto Complete" },
			{ key: "Components-Cascader", label: "Cascader" },
			{ key: "Components-ColorPicker", label: "Color Picker" },
			{ key: "Components-Checkbox", label: "Checkbox" },
			{ key: "Components-DatePicker", label: "Date Picker" },
			{ key: "Components-DynamicInput", label: "Dynamic Input" },
			{ key: "Components-DynamicTags", label: "Dynamic Tags" },
			{ key: "Components-Form", label: "Form" },
			{ key: "Components-Input", label: "Input" },
			{ key: "Components-InputNumber", label: "Input Number" },
			{ key: "Components-Mention", label: "Mention" },
			{ key: "Components-Radio", label: "Radio" },
			{ key: "Components-Rate", label: "Rate" },
			{ key: "Components-Select", label: "Select" },
			{ key: "Components-Slider", label: "Slider" },
			{ key: "Components-Switch", label: "Switch" },
			{ key: "Components-TimePicker", label: "Time Picker" },
			{ key: "Components-Transfer", label: "Transfer" },
			{ key: "Components-TreeSelect", label: "Tree Select" },
			{ key: "Components-Upload", label: "Upload" }
		]
	},
	{
		key: "Components-Group-Data-Display",
		label: "Data Display",
		items: [
			{ key: "Components-Calendar", label: "Calendar" },
			{ key: "Components-Countdown", label: "Countdown" },
			{ key: "Components-DataTable", label: "Data Table" },
			{ key: "Components-Descriptions", label: "Descriptions" },
			{ key: "Components-Empty", label: "Empty" },
			{ key: "Components-Image", label: "Image" },
			{ key: "Components-List", label: "List" },
			{ key: "Components-NumberAnimation", label: "Number Animation" },
			{ key: "Components-Scrollbar", label: "Scrollbar" },
			{ key: "Components-Statistic", label: "Statistic" },
			{ key: "Components-Table", label: "Table" },
			{ key: "Components-Thing", label: "Thing" },
			{ key: "Components-Time", label: "Time" },
			{ key: "Components-Timeline", label: "Timeline" },
			{ key: "Components-Tree", label: "Tree" }
		]
	},
	{
		key: "Components-Group-Navigation",
		label: "Navigation",
		items: [
			{ key: "Components-Affix", label: "Affix" },
			{ key: "Components-Anchor", label: "Anchor" },
			{ key: "Components-BackTop", label: "Back Top" },
			{ key: "Components-Breadcrumb", label: "Breadcrumb" },
			{ key: "Components-Menu", label: "Menu" },
			{ key: "Components-Pagination", label: "Pagination" },
			{ key: "Components-Steps", label: "Steps" },
			{ key: "Components-Tabs", label: "Tabs" }
		]
	},
	{
		key: "Components-Group-Feedback",
		label: "Feedback",
		items: [
			{ key: "Components-Alert", label: "Alert" },
			{ key: "Components-Badge", label: "Badge" },
			{ key: "Components-Dialog", label: "Dialog" },
			{ key: "Components-Drawer", label: "Drawer" },
			{ key: "Components-Message", label: "Message" },
			{ key: "Components-Modal", label: "Modal" },
			{ key: "Components-Notification", label: "Notification" },
			{ key: "Components-Popconfirm", label: "Popconfirm" },
			{ key: "Components-Popover", label: "Popover" },
			{ key: "Components-Popselect", label: "Popselect" },
			{ key: "Components-Progress", label: "Progress" },
			{ key: "Components-Result", label: "Result" },
			{ key: "Components-Skeleton", label: "Skeleton" },
			{ key: "Components-Spin", label: "Spin" },
			{ key: "Components-Tooltip", label: "Tooltip" }
		]
	},
	{
		key: "Components-Group-Layout",
		label: "Layout",
		items: [
			{ key: "Components-Layout", label: "Layout" },
			{ key: "Components-LegacyGrid", label: "Legacy Grid" },
			{ key: "Components-Grid", label: "Grid" },
			{ key: "Components-Space", label: "Space" }
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
