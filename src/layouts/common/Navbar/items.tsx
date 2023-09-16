import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"
import { type MenuMixedOption } from "naive-ui/es/menu/src/interface"

import BlankIcon from "@vicons/carbon/DocumentBlank"
import EmailIcon from "@vicons/carbon/Email"
import ChatIcon from "@vicons/carbon/Chat"
import KanbanIcon from "@vicons/fluent/GridKanban20Regular"
import NotesIcon from "@vicons/carbon/Notebook"
import TypographyIcon from "@vicons/fluent/TextFont16Regular"
import MultiLanguageIcon from "@vicons/ionicons5/LanguageOutline"
import GroupIcon from "@vicons/carbon/TreeView"
import CalendarIcon from "@vicons/carbon/Calendar"

import dashboard from "./dashboard"
//import calendars from "./calendars"
import cards from "./cards"
import getComponents from "./components"
import icons from "./icons"
import tables from "./tables"
import layout from "./layout"
import maps from "./maps"
import editors from "./editors"
import charts from "./charts"
import toolbox from "./toolbox"
import authentication from "./authentication"

export default function getItems(mode: "vertical" | "horizontal", collapsed: boolean): MenuMixedOption[] {
	return [
		dashboard,
		//calendars,
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "calendar"
						}
					},
					{ default: () => "Calendar" }
				),
			key: "calendar",
			icon: renderIcon(CalendarIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "email"
						}
					},
					{ default: () => "Email" }
				),
			key: "email",
			icon: renderIcon(EmailIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "chat"
						}
					},
					{ default: () => "Chat" }
				),
			key: "chat",
			icon: renderIcon(ChatIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "kanban"
						}
					},
					{ default: () => "Kanban" }
				),
			key: "kanban",
			icon: renderIcon(KanbanIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "notes"
						}
					},
					{ default: () => "Notes" }
				),
			key: "notes",
			icon: renderIcon(NotesIcon)
		},
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
							name: "multi-language"
						}
					},
					{ default: () => "Multi Language" }
				),
			key: "multi-language",
			icon: renderIcon(MultiLanguageIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "typography"
						}
					},
					{ default: () => "Typography" }
				),
			key: "typography",
			icon: renderIcon(TypographyIcon)
		},
		authentication,
		icons,
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
