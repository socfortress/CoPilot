<template>
	<div class="email flex items-center" :class="{ selected: email.selected, seen: email.seen }" @click="select(email)">
		<div class="check">
			<n-checkbox :checked="email.selected" @click.stop="toggleCheck(email)" size="large" />
		</div>
		<div class="starred flex" :class="{ 'opacity-50': !email.starred }">
			<n-button text @click.stop="toggleStar(email)">
				<Icon :size="16" :name="StarActiveIcon" v-if="email.starred" :color="primaryColor"></Icon>
				<Icon :size="16" :name="StarIcon" v-else></Icon>
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
			<Icon
				:size="16"
				v-for="label of email.labels"
				:key="label.id"
				:color="labelsColors[label.id]"
				:name="LabelIcon"
			></Icon>
		</div>
		<div class="attachments flex" v-if="email.attachments.length">
			<Icon :size="16" :name="AttachmentIcon"></Icon>
		</div>
		<div class="date text-secondary-color">
			{{ email.dateText }}
		</div>
		<div class="actions text-secondary-color flex items-start gap-3">
			<n-button text>
				<Icon :size="20" :name="TrashIcon"></Icon>
			</n-button>
			<n-button text>
				<Icon :size="20" :name="LabelOutIcon"></Icon>
			</n-button>
			<n-button text>
				<Icon :size="20" :name="FolderIcon"></Icon>
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NCheckbox, NAvatar, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const StarActiveIcon = "carbon:star-filled"
const StarIcon = "carbon:star"
const TrashIcon = "carbon:trash-can"
const LabelIcon = "carbon:bookmark-filled"
const LabelOutIcon = "carbon:bookmark"
const AttachmentIcon = "carbon:attachment"
const FolderIcon = "carbon:folder-move-to"
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
	border-bottom: var(--border-small-050);
	gap: 18px;
	line-height: 1.2;
	white-space: nowrap;
	cursor: pointer;
	transition: all 0.1s ease-in;
	container-type: inline-size;

	.title {
		overflow: hidden;
		width: 0;
		text-overflow: ellipsis;
		font-size: 15px;

		.name {
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
		background-color: var(--bg-secondary-color);
		.title {
			opacity: 0.85;
			.subject {
				font-weight: normal;
			}
		}
	}

	&.selected {
		background-color: var(--primary-005-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-050-color) inset;

		.actions {
			display: flex;
		}
		.labels,
		.attachments,
		.date {
			display: none;
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
