import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import EditorIcon from "@vicons/carbon/Pen"

export default {
	label: "Editors",
	key: "editors",
	icon: renderIcon(EditorIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "editors-quill"
						}
					},
					{ default: () => "Quill" }
				),
			key: "editors-quill"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "editors-tiptap"
						}
					},
					{ default: () => "Tiptap" }
				),
			key: "editors-tiptap"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "editors-milkdown"
						}
					},
					{ default: () => "Milkdown" }
				),
			key: "editors-milkdown"
		}
	]
}
