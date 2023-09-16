<template>
	<div class="email flex items-center" :class="{ selected: email.selected, seen: email.seen }" @click="select(email)">
		<div class="check">
			<n-checkbox :checked="email.selected" @click.stop="toggleCheck(email)" size="large" />
		</div>
		<div class="starred flex" :class="{ 'opacity-50': !email.starred }">
			<n-button text @click.stop="toggleStar(email)">
				<n-icon :size="16">
					<StarActiveIcon v-if="email.starred" :color="primaryColor" />
					<StarIcon v-else />
				</n-icon>
			</n-button>
		</div>
		<div class="avatar flex">
			<n-avatar round size="small" :src="email.avatar" />
		</div>
		<div class="title grow">
			<span class="name">
				{{ email.name }}
			</span>
			<span class="subject">
				{{ email.subject }}
			</span>
		</div>
		<div class="labels flex">
			<n-icon :size="16" v-for="label of email.labels" :key="label.id">
				<LabelIcon :color="labelsColors[label.id]" />
			</n-icon>
		</div>
		<div class="attachments flex" v-if="email.attachments.length">
			<n-icon :size="16">
				<AttachmentIcon />
			</n-icon>
		</div>
		<div class="date opacity-70">
			{{ email.dateText }}
		</div>
		<div class="actions opacity-70 flex items-start gap-3">
			<n-button text>
				<n-icon :size="20">
					<TrashIcon />
				</n-icon>
			</n-button>
			<n-button text>
				<n-icon :size="20">
					<LabelOutIcon />
				</n-icon>
			</n-button>
			<n-button text>
				<n-icon :size="20">
					<FolderIcon />
				</n-icon>
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NIcon, NCheckbox, NAvatar, NButton } from "naive-ui"
import StarActiveIcon from "@vicons/carbon/StarFilled"
import StarIcon from "@vicons/carbon/Star"
import TrashIcon from "@vicons/carbon/TrashCan"
import LabelIcon from "@vicons/carbon/BookmarkFilled"
import LabelOutIcon from "@vicons/carbon/Bookmark"
import AttachmentIcon from "@vicons/carbon/Attachment"
import FolderIcon from "@vicons/carbon/FolderMoveTo"
import { useMailboxStore } from "@/stores/apps/useMailboxStore"
import { type Email } from "@/mock/mailbox"
import { toRefs, computed } from "vue"
import { useThemeStore } from "@/stores/theme"

defineOptions({
	name: "Email"
})

const props = defineProps<{
	email: Email
}>()
const { email } = toRefs(props)

const emit = defineEmits<{
	(e: "select", value: Email): void
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

function select(email: Email) {
	emit("select", email)
}

function toggleCheck(email: Email) {
	store.toggleCheck(email)
}

function toggleStar(email: Email) {
	store.toggleStar(email)
}
</script>

<style lang="scss" scoped>
.email {
	height: 52px;
	padding: 0 30px;
	border-block-end: var(--border-small-050);
	gap: 18px;
	line-height: 1.2;
	white-space: nowrap;
	cursor: pointer;
	opacity: 0;
	transition: all 0.25s ease-in;
	animation: email-fade 0.3s forwards;
	container-type: inline-size;

	@for $i from 0 through 40 {
		&:nth-child(#{$i}) {
			animation-delay: $i * 0.05s;
		}
	}

	.title {
		overflow: hidden;
		width: 0;
		text-overflow: ellipsis;
		font-size: 15px;

		.name {
			//font-weight: bold;
			margin-right: 14px;
		}
		.subject {
			font-weight: bold;
		}
	}

	.actions {
		display: none;
	}

	&.seen {
		background-color: var(--bg-sidebar);
		.title {
			opacity: 0.85;
			.subject {
				font-weight: normal;
			}
		}
	}

	&.selected {
		background-color: rgba(var(--primary-color-rgb), 0.05);
	}

	&:hover {
		background-color: rgba(var(--bg-color-rgb), 0.03);
		border-bottom-color: transparent;
		box-shadow: 0px 1px 8px -4px rgba(var(--fg-color-rgb), 0.6);
		transform: translateY(-1px);

		.actions {
			display: flex;
		}
		.labels,
		.attachments,
		.date {
			display: none;
		}
	}

	@keyframes email-fade {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
		}
	}

	@container (max-width: 760px) {
		.title {
			display: flex;
			flex-direction: column;

			.name,
			.subject {
				overflow: hidden;
				text-overflow: ellipsis;
			}
		}
	}
	@container (max-width: 500px) {
		.avatar {
			display: none;
		}
	}
	@container (max-width: 360px) {
		.labels {
			display: none;
		}
	}
}

@media (max-width: 700px) {
	.email {
		gap: 14px;
		padding: 0 20px;

		.title {
			font-size: 14px;
		}
	}
}
</style>
