import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"
import { type MenuMixedOption } from "naive-ui/es/menu/src/interface"

const BlankIcon = "carbon:document-blank"
const TypographyIcon = "fluent:text-font-16-regular"
const MultiLanguageIcon = "ion:language-outline"
const GroupIcon = "carbon:tree-view"
const IconsIcon = "fluent:icons-24-regular"

import dashboard from "./dashboard"
import calendars from "./calendars"
import apps from "./apps"
import cards from "./cards"
import getComponents from "./components"
import tables from "./tables"
import layout from "./layout"
import maps from "./maps"
import editors from "./editors"
import charts from "./charts"
import toolbox from "./toolbox"
import authentication from "./authentication"

export default function getItems(mode: "vertical" | "horizontal", collapsed: boolean): MenuMixedOption[] {
	return [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Indices"
						}
					},
					{ default: () => "Indices" }
				),
			key: "Indices",
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Agents"
						}
					},
					{ default: () => "Agents" }
				),
			key: "Agents",
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Connectors"
						}
					},
					{ default: () => "Connectors" }
				),
			key: "Connectors",
			icon: renderIcon(BlankIcon)
		},
		{
			label: "Graylog",
			key: "Graylog",
			icon: renderIcon(BlankIcon),
			children: [
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Graylog-Management"
								}
							},
							{ default: () => "Management" }
						),
					key: "Graylog-Management"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Graylog-Metrics"
								}
							},
							{ default: () => "Metrics" }
						),
					key: "Graylog-Metrics"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Graylog-Pipelines"
								}
							},
							{ default: () => "Pipelines" }
						),
					key: "Graylog-Pipelines"
				}
			]
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Alerts"
						}
					},
					{ default: () => "Alerts" }
				),
			key: "Alerts",
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Artifacts"
						}
					},
					{ default: () => "Artifacts" }
				),
			key: "Artifacts",
			icon: renderIcon(BlankIcon)
		},
		{
			type: "divider"
		},

		dashboard,
		calendars,
		...apps,
		{
			key: "divider-1",
			type: "divider",
			props: {
				style: {
					//marginLeft: "32px"
				}
			}
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Icons"
						}
					},
					{ default: () => "Icons" }
				),
			key: "Icons",
			icon: renderIcon(IconsIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Typography"
						}
					},
					{ default: () => "Typography" }
				),
			key: "Typography",
			icon: renderIcon(TypographyIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "MultiLanguage"
						}
					},
					{ default: () => "Multi Language" }
				),
			key: "MultiLanguage",
			icon: renderIcon(MultiLanguageIcon)
		},
		authentication,
		cards,
		tables,
		getComponents(),
		maps,
		charts,
		editors,
		layout,
		toolbox,
		{
			label: () => (
				<div class={"item-badge"}>
					<div>Disabled item</div>
					<div>3</div>
				</div>
			),
			key: "Disabled item",
			icon: renderIcon(BlankIcon),
			disabled: true,
			children: [
				{
					label: "Disabled item a",
					key: "Disabled item a"
				}
			]
		},
		{
			label: "Multi level",
			key: "multi-level",
			icon: renderIcon(BlankIcon),
			children: [
				{
					label: "With icon",
					key: "With icon",
					icon: renderIcon(BlankIcon),
					children: [
						{
							label: "Level three A",
							key: "Level three",
							children: [
								{
									label: "Level four",
									key: "Level four",
									children: [
										{
											label: "Level five",
											key: "Level five"
										}
									]
								}
							]
						}
					]
				},
				{
					label: "Without icon",
					key: "Without icon",
					children: [
						{
							label: "Level three B",
							key: "Level three B"
						}
					]
				},
				{
					label: "Long text, long text, long text, long text",
					key: "Long text, long text, long text, long text"
				},
				{
					type: "group",
					label: "Group",
					key: "group",
					children: [
						{
							label: "Level two A",
							key: "level two A",
							icon: renderIcon(BlankIcon)
						},
						{
							label: "Level two B",
							key: "level two B",
							icon: renderIcon(BlankIcon)
						}
					]
				}
			]
		},
		{
			label: "Group items",
			key: "group-items",
			type: mode === "vertical" && !collapsed ? "group" : undefined,
			icon: renderIcon(GroupIcon),
			children: [
				{
					label: "Level two A",
					key: "level two A",
					icon: renderIcon(BlankIcon)
				},
				{
					label: "Level two B",
					key: "level two B",
					icon: renderIcon(BlankIcon)
				}
			]
		}
	]
}
