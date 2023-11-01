<template>
	<div class="email-view flex flex-col">
		<div class="email-view-toolbar flex items-center">
			<n-button text @click="goBack()">
				<Icon :size="24" :name="ArrowLeftIcon" />
			</n-button>
			<div class="actions-btns flex items-center gap-2">
				<n-tooltip>
					<template #trigger>
						<n-button text>
							<Icon :size="20" :name="TrashIcon" />
						</n-button>
					</template>
					<span>Delete</span>
				</n-tooltip>
				<n-tooltip>
					<template #trigger>
						<n-button text>
							<Icon :size="20" :name="LabelOutIcon" />
						</n-button>
					</template>
					<span>Add label</span>
				</n-tooltip>
				<n-tooltip>
					<template #trigger>
						<n-button text>
							<Icon :size="20" :name="FolderIcon" />
						</n-button>
					</template>
					<span>Move to folder</span>
				</n-tooltip>
				<n-tooltip>
					<template #trigger>
						<n-button text>
							<Icon :size="20" :name="PrinterIcon" />
						</n-button>
					</template>
					<span>Print</span>
				</n-tooltip>
				<n-tooltip>
					<template #trigger>
						<n-button text @click.stop="toggleStar(email)">
							<Icon :size="20" :name="StarActiveIcon" v-if="email.starred" :color="primaryColor" />
							<Icon :size="20" :name="StarIcon" v-else />
						</n-button>
					</template>
					<span>Star</span>
				</n-tooltip>
			</div>
			<div class="menu-btns flex items-center">
				<n-dropdown :options="menuOptions">
					<n-button text>
						<Icon :size="24" :name="MenuHorizontalIcon" />
					</n-button>
				</n-dropdown>
			</div>
			<div class="grow"></div>
			<div class="reply-btns flex items-center gap-2">
				<n-button text>
					<Icon :size="20" :name="ReplyIcon" />
				</n-button>
				<n-button text>
					<Icon :size="20" :name="ReplyAllIcon" />
				</n-button>
				<n-button text>
					<Icon :size="20" :name="ForwardIcon" />
				</n-button>
			</div>
			<div class="nav-btns flex items-center gap-2">
				<span class="opacity-70">1 - 30 of 635</span>
				<n-button text size="small">
					<Icon :size="24" :name="ChevronLeftIcon" />
				</n-button>
				<n-button text size="small">
					<Icon :size="24" :name="ChevronRightIcon" />
				</n-button>
			</div>
		</div>
		<div class="email-view-content grow">
			<n-scrollbar style="max-height: 100%">
				<div class="email-view-sender flex flex-wrap items-center">
					<div class="avatar flex">
						<n-avatar round :size="45" :src="email.avatar" />
					</div>
					<div class="info grow flex flex-wrap items-center">
						<div class="title grow flex flex-col">
							<span class="name">
								{{ email.name }}
							</span>
							<span class="email">
								{{ email.email }}
							</span>
						</div>
						<div class="date">
							<n-time :time="email.date" format="d MMM @ HH:mm" />
						</div>
					</div>
				</div>
				<div class="email-view-subject">
					<span class="subject">
						{{ email.subject }}
					</span>
					<span
						class="label custom-label"
						v-for="label of email.labels"
						:key="label.id"
						:style="`--label-color:${labelsColors[label.id]}`"
					>
						{{ label.title }}
					</span>
				</div>
				<div class="email-view-body" v-html="email.body"></div>
				<div class="email-view-attachments flex flex-wrap" v-if="email.attachments.length">
					<div class="attachment-item flex" v-for="attachment of email.attachments" :key="attachment.name">
						<div class="attachment-icon">
							<Icon :size="26" :name="FileIcon" />
						</div>
						<div class="attachment-info">
							<div class="attachment-name">{{ attachment.name }}</div>
							<div class="attachment-size">{{ attachment.size }}</div>
						</div>
					</div>
				</div>
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar, NAvatar, NButton, NTime, NTooltip, NDropdown } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useMailboxStore } from "@/stores/apps/useMailboxStore"
import { toRefs, computed } from "vue"
import { type Email } from "@/mock/mailbox"
import { renderIcon } from "@/utils"
import { useThemeStore } from "@/stores/theme"

const StarActiveIcon = "carbon:star-filled"
const StarIcon = "carbon:star"
const TrashIcon = "carbon:trash-can"
const LabelOutIcon = "carbon:bookmark"
const MenuHorizontalIcon = "carbon:overflow-menu-horizontal"
const FolderIcon = "carbon:folder-move-to"
const ArrowLeftIcon = "carbon:arrow-left"
const ChevronLeftIcon = "carbon:chevron-left"
const ChevronRightIcon = "carbon:chevron-right"
const PrinterIcon = "carbon:printer"
const FileIcon = "tabler:file-invoice"
const ReplyAllIcon = "fluent:arrow-reply-all-20-filled"
const ReplyIcon = "fluent:arrow-reply-20-filled"
const ForwardIcon = "fluent:arrow-forward-20-filled"

const props = defineProps<{
	email: Email
}>()
const { email } = toRefs(props)

const emit = defineEmits<{
	(e: "back"): void
}>()

const store = useMailboxStore()

const primaryColor = computed(() => useThemeStore().primaryColor)

const secondaryColors = computed(() => useThemeStore().secondaryColors)

const labelsColors = {
	personal: secondaryColors.value["secondary1"],
	office: secondaryColors.value["secondary2"],
	important: secondaryColors.value["secondary3"],
	shop: secondaryColors.value["secondary4"]
} as unknown as { [key: string]: string }

function toggleStar(email: Email) {
	store.toggleStar(email)
}

function goBack() {
	emit("back")
}

const menuOptions = [
	{
		label: "Delete",
		key: "Delete",
		icon: renderIcon(TrashIcon)
	},
	{
		label: "Add label",
		key: "Add label",
		icon: renderIcon(LabelOutIcon)
	},
	{
		label: "Move to folder",
		key: "Move to folder",
		icon: renderIcon(FolderIcon)
	},
	{
		label: "Print",
		key: "Print",
		icon: renderIcon(PrinterIcon)
	},
	{
		label: "Star",
		key: "Star",
		icon: renderIcon(StarIcon)
	}
]
</script>

<style lang="scss" scoped>
.email-view {
	--mb-toolbar-height: 70px;

	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	width: 100%;
	height: 100%;
	background-color: var(--bg-color);
	animation: email-view 0.25s forwards ease-out;
	overflow: hidden;

	.email-view-toolbar {
		border-block-end: var(--border-small-050);
		min-height: var(--mb-toolbar-height);
		padding: 0 30px;
		gap: 18px;

		.actions-btns {
			gap: 18px;
		}

		.menu-btns {
			display: none;
		}

		.reply-btns {
			margin-right: 15px;
		}

		@container (max-width:600px) {
			.nav-btns {
				span {
					display: none;
				}
			}
		}
		@container (max-width:500px) {
			.actions-btns {
				display: none;
			}
			.menu-btns {
				display: flex;
			}
		}
	}

	.email-view-content {
		overflow: hidden;

		.email-view-sender {
			gap: 18px;
			padding: 20px 30px;

			.title {
				margin-right: 30px;
				.name {
					font-size: 18px;
				}
				.email {
					opacity: 0.8;
				}
			}

			.date {
				font-size: 16px;
				opacity: 0.7;
			}
		}

		.email-view-subject {
			padding: 0px 30px;
			line-height: 1.25;

			.subject {
				font-size: 20px;
				font-weight: bold;
				margin-right: 10px;
			}
			.label {
				top: -2px;
			}
		}

		.email-view-body {
			padding: 20px 30px;
			line-height: 1.35;
			font-size: 16px;
		}

		.email-view-attachments {
			padding: 20px 30px;
			gap: 20px;

			.attachment-item {
				background-color: var(--primary-010-color);
				padding: 14px;
				border-radius: var(--border-radius);
				max-width: 100%;

				.attachment-icon {
					margin-top: 3px;
					margin-right: 10px;
				}

				.attachment-info {
					padding-right: 5px;
					line-height: 1.4;
					.attachment-name {
						font-size: 14px;
						word-break: break-all;
						line-height: 1.2;
					}
					.attachment-size {
						font-size: 10px;
						opacity: 0.5;
						margin-top: 3px;
					}
				}
			}
		}
	}

	@keyframes email-view {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	@media (max-width: 700px) {
		--mb-toolbar-height: 62px;
	}
}
</style>
