<template>
	<article class="flex flex-col gap-3" :data-testid="`announcement-${announcement.id}`">
		<div v-if="announcement.image_url && !imageFailed" class="overflow-hidden rounded-lg">
			<img
				:src="announcement.image_url"
				:alt="announcement.image_alt"
				class="block max-h-56 w-full object-cover"
				loading="lazy"
				referrerpolicy="no-referrer"
				data-testid="announcement-image"
				@error="imageFailed = true"
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2 text-xs">
			<n-tag :type="category.type" size="small" :bordered="false" data-testid="announcement-category">
				{{ category.label }}
			</n-tag>
			<n-tag v-if="isNew" type="primary" size="small" round data-testid="announcement-new">New</n-tag>
			<span class="text-secondary">{{ formatDate(announcement.published_at, dFormats.date) }}</span>
		</div>

		<div class="text-base leading-snug font-semibold">{{ announcement.title }}</div>
		<div v-if="announcement.summary" class="text-secondary text-sm">{{ announcement.summary }}</div>

		<template v-if="announcement.body_markdown">
			<Markdown
				v-if="expanded || full"
				:source="announcement.body_markdown"
				no-images
				class="text-sm"
				data-testid="announcement-body"
			/>
			<n-button v-if="!full" text size="small" class="self-start" @click="expanded = !expanded">
				{{ expanded ? "Show less" : "Read more" }}
			</n-button>
		</template>

		<n-button
			v-if="announcement.cta"
			tag="a"
			:href="announcement.cta.url"
			target="_blank"
			rel="noopener noreferrer"
			type="primary"
			size="small"
			secondary
			class="self-start"
			data-testid="announcement-cta"
		>
			{{ announcement.cta.label }}
			<template #icon>
				<Icon name="carbon:launch" :size="14" />
			</template>
		</n-button>
	</article>
</template>

<script setup lang="ts">
import type { Announcement, AnnouncementCategory } from "@/types/announcements"
import { NButton, NTag } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const {
	announcement,
	isNew = false,
	full = false
} = defineProps<{
	announcement: Announcement
	isNew?: boolean
	/** Show the whole body (the sign-in modal), rather than behind "Read more" (the drawer). */
	full?: boolean
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

type TagType = "default" | "info" | "success" | "warning" | "error" | "primary"

const CATEGORIES: Record<AnnouncementCategory, { label: string; type: TagType }> = {
	product: { label: "New product", type: "info" },
	release: { label: "Release", type: "success" },
	advisory: { label: "Advisory", type: "warning" },
	event: { label: "Event", type: "default" },
	promotion: { label: "Offer", type: "default" }
}

const dFormats = useSettingsStore().dateFormat
const expanded = ref(false)
const imageFailed = ref(false)
const category = computed(() => CATEGORIES[announcement.category] ?? { label: announcement.category, type: "default" })
</script>
