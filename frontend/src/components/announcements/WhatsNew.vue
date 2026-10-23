<template>
	<template v-if="visible">
		<n-tooltip placement="bottom">
			<template #trigger>
				<button
					type="button"
					class="flex cursor-pointer items-center"
					:aria-label="unseen.length ? `What's new (${unseen.length} unread)` : `What's new`"
					data-testid="whats-new-trigger"
					@click="openDrawer"
				>
					<n-badge :show="unseen.length > 0" dot :color="primaryColor" data-testid="whats-new-dot">
						<Icon :name="MegaphoneIcon" :size="20" class="text-default" />
					</n-badge>
				</button>
			</template>
			What's new from SOCFortress
		</n-tooltip>

		<n-drawer v-model:show="showDrawer" :width="440" class="max-w-[90vw]" :trap-focus="false">
			<n-drawer-content title="What's new from SOCFortress" closable data-testid="whats-new-drawer">
				<div class="flex flex-col">
					<template v-for="(item, index) of announcements" :key="item.id">
						<n-divider v-if="index > 0" />
						<AnnouncementCard :announcement="item" :is-new="newWhenOpened.has(item.id)" />
					</template>
				</div>
			</n-drawer-content>
		</n-drawer>

		<n-modal
			v-model:show="showModal"
			preset="card"
			:title="modalTitle"
			class="max-w-[90vw]"
			style="width: 560px"
			:mask-closable="false"
			data-testid="whats-new-modal"
			@after-leave="modalItems = []"
		>
			<AnnouncementCard v-if="modalItem" :key="modalItem.id" :announcement="modalItem" full />
			<template #footer>
				<div class="flex items-center justify-between gap-3">
					<span
						v-if="modalItems.length > 1"
						class="text-secondary text-sm"
						data-testid="whats-new-modal-page"
					>
						{{ modalIndex + 1 }} of {{ modalItems.length }}
					</span>
					<span v-else></span>
					<div class="flex gap-2">
						<n-button v-if="modalIndex > 0" size="small" @click="modalIndex -= 1">Previous</n-button>
						<n-button
							v-if="modalIndex < modalItems.length - 1"
							size="small"
							type="primary"
							data-testid="whats-new-modal-next"
							@click="modalIndex += 1"
						>
							Next
						</n-button>
						<n-button
							v-else
							size="small"
							type="primary"
							data-testid="whats-new-modal-done"
							@click="showModal = false"
						>
							Got it
						</n-button>
					</div>
				</div>
			</template>
		</n-modal>
	</template>
</template>

<script setup lang="ts">
import type { Announcement } from "@/types/announcements"
import { NBadge, NButton, NDivider, NDrawer, NDrawerContent, NModal, NTooltip } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useAnnouncements } from "@/composables/useAnnouncements"
import { useThemeStore } from "@/stores/theme"
import AnnouncementCard from "./AnnouncementCard.vue"

const MegaphoneIcon = "carbon:bullhorn"

const { announcements, enabled, unseen, popupQueue, load, markSeen, modalAlreadyShown, rememberModalShown } =
	useAnnouncements()

const themeStore = useThemeStore()
const primaryColor = computed(() => themeStore.style["primary-color"])

const visible = computed(() => enabled.value && announcements.value.length > 0)

const showDrawer = ref(false)
// What was unread when the drawer opened: tagged "New" while it stays open, though opening it
// marks everything read (the dot goes).
const newWhenOpened = ref(new Set<string>())

function openDrawer() {
	newWhenOpened.value = new Set(unseen.value.map(a => a.id))
	showDrawer.value = true
	markSeen(announcements.value.map(a => a.id))
}

const showModal = ref(false)
const modalItems = ref<Announcement[]>([])
const modalIndex = ref(0)
const modalItem = computed(() => modalItems.value[modalIndex.value] ?? null)
const modalTitle = computed(() =>
	modalItems.value.length > 1 ? "What's new from SOCFortress" : "New from SOCFortress"
)

function maybeShowModal() {
	if (showModal.value || modalAlreadyShown() || !popupQueue.value.length) return
	modalItems.value = [...popupQueue.value]
	modalIndex.value = 0
	showModal.value = true
	// Shown once: the items count as seen whether the user pages through them or closes the modal.
	rememberModalShown()
	markSeen(modalItems.value.map(a => a.id))
}

watch(popupQueue, maybeShowModal)

onMounted(async () => {
	await load()
	maybeShowModal()
})
</script>
