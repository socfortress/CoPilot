<template>
	<div class="flex items-center search-btn" @click="openBox" ref="searchBtn">
		<n-icon size="16">
			<SearchOutline />
		</n-icon>
		<span>Search</span>
		<n-text code class="search-command">
			<span :class="{ win: commandIcon === 'CTRL' }">{{ commandIcon }}</span>
			K
		</n-text>
	</div>
	<n-modal v-model:show="showSearchBox" class="search-box-modal">
		<n-card
			style="width: 600px"
			content-style="padding: 0;"
			:bordered="false"
			size="huge"
			role="dialog"
			aria-modal="true"
		>
			<div class="search-box">
				<div class="search-input flex items-center">
					<n-icon size="16">
						<SearchOutline />
					</n-icon>
					<input placeholder="Search" v-model="search" class="grow" />
					<n-text code>ESC</n-text>
					<n-icon size="20" @click="closeBox()" class="cursor-pointer">
						<CloseIcon />
					</n-icon>
				</div>
				<n-divider />
				<n-scrollbar style="height: 400px" ref="scrollContent">
					<div class="conten-wrap">
						<div class="group" v-for="group of filteredGroups" :key="group.name">
							<div class="group-title">{{ group.name }}</div>
							<div class="group-list">
								<div
									v-for="item of group.items"
									:key="item.key"
									:id="item.key.toString()"
									class="item flex items-center"
									:class="{ active: item.key === activeItem }"
									v-element-hover="
										() => {
											activeItem = item.key
										}
									"
									@click="callAction(item.action)"
								>
									<div class="icon">
										<n-avatar v-if="item.iconImage" round :size="28" :src="item.iconImage" />
										<n-icon
											v-if="item.iconComponent"
											size="18"
											:component="item.iconComponent"
										></n-icon>
									</div>
									<div class="title grow">
										<Highlighter
											highlightClassName="highlight"
											:searchWords="keywords"
											:autoEscape="true"
											:textToHighlight="item.title"
										/>
									</div>
									<div class="label">{{ item.label }}</div>
								</div>
							</div>
						</div>
						<div v-if="!filteredGroups.length" class="group-empty">
							We couldn't find anything matching "{{ search }}"
						</div>
					</div>
				</n-scrollbar>
				<n-divider />
				<div class="hint-bar flex items-center justify-center">
					<div class="hint flex items-center justify-center">
						<div class="icon">
							<n-icon size="12">
								<ArrowEnterLeft24Regular />
							</n-icon>
						</div>
						<span class="label">to select</span>
					</div>
					<div class="hint flex items-center justify-center">
						<div class="icon">
							<n-icon size="12">
								<ArrowSort24Regular />
							</n-icon>
						</div>
						<span class="label">to navigate</span>
					</div>
				</div>
			</div>
		</n-card>
	</n-modal>
</template>

<script lang="ts" setup>
import { type DefineComponent, type Raw, computed, shallowRef, onMounted, ref, watch, type ShallowRef } from "vue"
import { NIcon, NText, NModal, NCard, NDivider, NAvatar, NScrollbar, type ScrollbarInst } from "naive-ui"
import SearchOutline from "@vicons/ionicons5/SearchOutline"
import TaskListSquareAdd20Regular from "@vicons/fluent/TaskListSquareAdd20Regular"
import MailEdit20Regular from "@vicons/fluent/MailEdit20Regular"
import ChartPerson20Regular from "@vicons/fluent/ChartPerson20Regular"
import ArrowEnterLeft24Regular from "@vicons/fluent/ArrowEnterLeft24Regular"
import FullScreenMaximize24Regular from "@vicons/fluent/FullScreenMaximize24Regular"
import MoonOutline from "@vicons/ionicons5/MoonOutline"
import ArrowSort24Regular from "@vicons/fluent/ArrowSort24Regular"
import CloseIcon from "@vicons/ionicons5/Close"
import { useMagicKeys } from "@vueuse/core"
import { faker } from "@faker-js/faker"
import Highlighter from "vue-highlight-words"
import { useRouter } from "vue-router"
import { vElementHover } from "@vueuse/components"
import { emitter } from "@/emitter"
import { getOS } from "@/utils"

interface GroupItem {
	iconComponent: DefineComponent | Raw<DefineComponent> | ShallowRef<DefineComponent> | null
	iconImage: string | null
	key: number | string
	title: string
	label: string
	tags?: string
	action: () => void
}

interface Group {
	name: string
	items: GroupItem[]
}
type Groups = Group[]

defineOptions({
	name: "Search"
})

const router = useRouter()

const showSearchBox = ref(false)
const search = ref("")
const activeItem = ref<null | string | number>(null)
const downupTimer = ref<NodeJS.Timeout | null>(null)
const searchBtn = ref<null | HTMLElement>(null)
const commandIcon = ref("⌘")
const scrollContent = ref<(ScrollbarInst & { $el: any }) | null>(null)

const groups = ref<Groups>([
	{
		name: "Applications",
		items: [
			{
				iconComponent: shallowRef(TaskListSquareAdd20Regular as DefineComponent),
				iconImage: null,
				key: 1,
				title: "Add todo list",
				label: "Shortcut",
				action() {
					router.push({ path: "/kanban" })
				}
			},
			{
				iconComponent: shallowRef(MailEdit20Regular as DefineComponent),
				iconImage: null,
				key: 2,
				title: "Compose new email",
				label: "Shortcut",
				action() {
					router.push({ path: "/email" })
				}
			},
			{
				iconComponent: shallowRef(ChartPerson20Regular as DefineComponent),
				iconImage: null,
				key: 3,
				title: "View Notes",
				label: "Shortcut",
				action() {
					router.push({ path: "/notes" })
				}
			}
		]
	},
	{
		name: "Contacts",
		items: [
			{
				iconComponent: null,
				iconImage: "https://i.pravatar.cc/56?_=" + Math.random(),
				key: 4,
				title: faker.person.fullName(),
				label: faker.internet.email().toLowerCase(),
				action() {
					router.push({ path: "/chat" })
				}
			},
			{
				iconComponent: null,
				iconImage: "https://i.pravatar.cc/56?_=" + Math.random(),
				key: 5,
				title: faker.person.fullName(),
				label: faker.internet.email().toLowerCase(),
				action() {
					router.push({ path: "/chat" })
				}
			},
			{
				iconComponent: null,
				iconImage: "https://i.pravatar.cc/56?_=" + Math.random(),
				key: 6,
				title: faker.person.fullName(),
				label: faker.internet.email().toLowerCase(),
				action() {
					router.push({ path: "/chat" })
				}
			}
		]
	},
	{
		name: "Actions",
		items: [
			{
				iconComponent: shallowRef(FullScreenMaximize24Regular as DefineComponent),
				iconImage: null,
				key: 7,
				title: "Toggle fullscreen",
				label: "Action",
				action() {
					emitter.emit("toggle:fullscreen")
				}
			},
			{
				iconComponent: shallowRef(MoonOutline as DefineComponent),
				iconImage: null,
				key: 8,
				title: "Toggle dark mode",
				label: "Action",
				action() {
					emitter.emit("toggle:darkmode")
				}
			}
		]
	}
])

const keywords = computed<string[]>(() => {
	if (search.value.length > 1) {
		return search.value.split(" ").filter(k => k)
	} else {
		return []
	}
})
const filteredGroups = computed<Groups>(() => {
	if (keywords.value.length === 0) {
		return groups.value
	}
	const newGroups: Groups = []
	for (const group of groups.value) {
		const items = group.items.filter(item => {
			if (keywords.value.filter(k => item.title.toLowerCase().indexOf(k.toLowerCase()) !== -1).length !== 0) {
				return true
			}
			if (
				item.tags &&
				keywords.value.filter(k => item.tags?.toLowerCase().indexOf(k.toLowerCase()) !== -1).length !== 0
			) {
				return true
			}
			return false
		})
		if (items.length) {
			newGroups.push({
				name: group.name,
				items
			})
		}
	}
	return newGroups
})

/*eslint  @typescript-eslint/no-unused-vars: "off"*/
const flattenItems = computed<GroupItem[]>(() => {
	const items = []

	for (const group of groups.value) {
		items.push(...group.items)
	}

	return items
})

const filteredFlattenItems = computed<GroupItem[]>(() => {
	const items = []

	for (const group of filteredGroups.value) {
		items.push(...group.items)
	}

	return items
})

function openBox(e?: MouseEvent) {
	if (!showSearchBox.value) {
		showSearchBox.value = true
		setTimeout(() => {
			search.value = ""
			activeItem.value = null
			if (downupTimer.value) {
				clearInterval(downupTimer.value)
			}
		}, 100)
	}
	return e
}
function closeBox() {
	showSearchBox.value = false
	search.value = ""
	activeItem.value = null
	if (downupTimer.value) {
		clearInterval(downupTimer.value)
	}
}
function callAction(action: () => void) {
	action()
	closeBox()
}
function nextItem() {
	const currentIndex = filteredFlattenItems.value.findIndex(item => item.key === activeItem.value)
	if (currentIndex === filteredFlattenItems.value.length - 1 || activeItem.value === null) {
		activeItem.value = filteredFlattenItems.value[0].key
	} else {
		activeItem.value = filteredFlattenItems.value[currentIndex + 1].key
	}
	centerItem()
}
function prevItem() {
	const currentIndex = filteredFlattenItems.value.findIndex(item => item.key === activeItem.value)
	if (currentIndex === 0 || activeItem.value === null) {
		activeItem.value = filteredFlattenItems.value[filteredFlattenItems.value.length - 1].key
	} else {
		activeItem.value = filteredFlattenItems.value[currentIndex - 1].key
	}
	centerItem()
}
function performAction() {
	const item = filteredFlattenItems.value.find(item => item.key === activeItem.value)
	if (item) {
		callAction(item.action)
	}
}
function centerItem() {
	const element = document.getElementById(activeItem.value?.toString() || "")
	if (element && scrollContent.value) {
		const wrap: HTMLElement = scrollContent.value.$el.nextSibling || scrollContent.value.$el.nextElementSibling
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent.value?.scrollTo({ top: middle })
	}
}

onMounted(() => {
	const isWindows = getOS() === "Windows"
	commandIcon.value = isWindows ? "CTRL" : "⌘"

	const keys = useMagicKeys()
	const ActiveCMD = isWindows ? keys["ctrl+k"] : keys["cmd+k"]
	const Up = keys["arrowup"]
	const Down = keys["arrowdown"]
	const Enter = keys["enter"]
	// const Esc = keys["escape"]

	watch(ActiveCMD, v => {
		if (v) searchBtn.value?.click()
	})

	watch(Down, v => {
		if (showSearchBox.value) {
			if (v) {
				nextItem()
				downupTimer.value = setInterval(() => {
					nextItem()
				}, 100)
			} else {
				if (downupTimer.value) {
					clearInterval(downupTimer.value)
				}
			}
		}
	})

	watch(Up, v => {
		if (showSearchBox.value) {
			if (v) {
				prevItem()
				downupTimer.value = setInterval(() => {
					prevItem()
				}, 100)
			} else {
				if (downupTimer.value) {
					clearInterval(downupTimer.value)
				}
			}
		}
	})

	watch(Enter, v => {
		if (showSearchBox.value) {
			if (v) {
				performAction()
			}
		}
	})
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/common.scss";
.search-btn {
	border-radius: 50px;
	background-color: var(--bg-body);
	gap: 10px;
	height: 32px;
	cursor: pointer;
	padding: 4px 10px;
	padding-right: 5px;
	outline: none;
	border: none;

	.search-command {
		span {
			line-height: 0;
			position: relative;
			top: 1px;
			font-size: 16px;

			&.win {
				font-size: inherit;
				top: 0;
			}
		}
	}

	:deep() {
		& > .n-icon {
			opacity: 0.5;
			transition: opacity 0.3s;
		}
	}
	& > span {
		opacity: 0.5;
		padding-right: 2px;
		font-size: 14px;
		transition: opacity 0.3s;
	}

	:deep() {
		& > code {
			background-color: var(--bg-sidebar);
			border-top-right-radius: 10px;
			border-bottom-right-radius: 10px;
			padding-right: 10px;
		}
	}

	&:hover {
		:deep() {
			& > .n-icon {
				opacity: 0.9;
			}
		}
		& > span {
			opacity: 0.9;
		}
	}

	@media (max-width: 1000px) {
		padding-right: 10px;

		& > span {
			display: none;
		}
		& > .n-text--code {
			display: none;
		}
	}
}

.search-box-modal {
	.search-box {
		border-radius: 4px;

		.search-input {
			height: 50px;
			gap: 20px;
			padding: 20px;

			input {
				background: transparent;
				outline: none;
				border: none;
				min-width: 100px;
			}

			.n-text--code {
				white-space: nowrap;
			}
		}

		.n-divider {
			margin-top: 0;
			margin-bottom: 0;
		}

		.conten-wrap {
			padding-bottom: 30px;

			.group-empty {
				text-align: center;
				padding: 30px 0 40px 0;
			}
			.group {
				padding: 0 10px;
				.group-title {
					opacity: 0.6;
					margin-bottom: 5px;
					padding: 5px 10px;
					padding-top: 20px;
				}
				.group-list {
					.item {
						padding: 7px 10px;
						gap: 10px;
						cursor: pointer;
						border-radius: 10px;

						.icon {
							width: 28px;
							height: 28px;
							border-radius: 50%;
							background-color: rgba(var(--primary-color-rgb), 0.05);
							display: flex;
							justify-content: center;
							align-items: center;
						}
						.title {
							font-weight: bold;
						}
						.label {
							opacity: 0.8;
							font-size: 0.9em;
						}

						&.active {
							background-color: rgba(var(--fg-color-rgb), 0.03);
						}
					}
				}
			}
		}

		.hint-bar {
			font-size: 12px;
			gap: 20px;
			padding: 10px 0;
			.icon {
				background-color: var(--code-color);
				width: 18px;
				height: 18px;
				padding-top: 1px;
				text-align: center;
				border-radius: 4px;
				margin-right: 5px;
				display: flex;
				align-items: center;
				justify-content: center;
			}
			.label {
				opacity: 0.7;
			}
		}
	}
}
</style>
