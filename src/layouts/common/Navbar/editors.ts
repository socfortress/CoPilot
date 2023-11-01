import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const EditorIcon = "carbon:pen"

export default {
	label: "Editors",
	key: "Editors",
	icon: renderIcon(EditorIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Editors-Quill"
						}
					},
					{ default: () => "Quill" }
				),
			key: "Editors-Quill"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Editors-Tiptap"
						}
					},
					{ default: () => "Tiptap" }
				),
			key: "Editors-Tiptap"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Editors-Milkdown"
						}
					},
					{ default: () => "Milkdown" }
				),
			key: "Editors-Milkdown"
		}
	]
}
