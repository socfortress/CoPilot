<template>
	<div class="flex flex-col gap-3">
		<n-spin :show="loading || loadingPreviews">
			<!-- n-image-group, not bare n-image: the lightbox then knows about the whole
			     page set, so a multi-page document is paged through with the arrows
			     instead of closing and reopening one page at a time. -->
			<n-image-group v-if="images.length">
				<div class="preview-grid grid gap-3">
					<n-image
						v-for="(src, i) of images"
						:key="i"
						:src
						:alt="previewNames[i] || `page ${i + 1}`"
						class="border-default overflow-hidden rounded-lg border"
						object-fit="contain"
					/>
				</div>
			</n-image-group>
			<n-empty
				v-else-if="!loading"
				description="No page previews — this file type has no rendered pages (e.g. an executable), or Tier 1 is still running."
				class="min-h-52 justify-center"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NEmpty, NImage, NImageGroup, NSpin, useMessage } from "naive-ui"
import { onBeforeUnmount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { MOCK_JOB_ID, mockPreview, USE_MOCK_ANALYSIS } from "@/components/fileAnalysis/mock-analysis"
import { getApiErrorMessage } from "@/utils"

// Renders authenticated PNG previews as object URLs — the browser never receives
// the raw file, only inert images produced inside the inspector container.
const props = defineProps<{ jobId: string; previewNames: string[]; loading?: boolean }>()
const { jobId, previewNames } = toRefs(props)

const message = useMessage()
const images = ref<string[]>([])
const loadingPreviews = ref(false)
let objectUrls: string[] = []
// Key of the currently-loaded preview set. The parent re-fetches the result on
// every status poll, handing us a NEW array each time — without this guard we'd
// revoke + re-download every page on each poll (the flicker). Load once per set.
let loadedKey = ""

// Session-lived blob cache (module scope, survives component unmount) so reopening
// a previously-viewed file is instant instead of re-downloading every page. The
// bytes are already saved server-side; this just avoids re-fetching them. Bounded
// so a long session doesn't grow without limit (oldest-out via Map insert order).
const BLOB_CACHE = new Map<string, Blob>()
const BLOB_CACHE_MAX = 400

function cachePut(key: string, blob: Blob) {
	if (BLOB_CACHE.size >= BLOB_CACHE_MAX) {
		const oldest = BLOB_CACHE.keys().next().value
		if (oldest !== undefined) BLOB_CACHE.delete(oldest)
	}
	BLOB_CACHE.set(key, blob)
}

function revoke() {
	objectUrls.forEach(url => URL.revokeObjectURL(url))
	objectUrls = []
}

async function loadPreviews() {
	const names = previewNames.value || []
	const key = `${jobId.value}::${names.join("|")}`
	if (key === loadedKey) return // same set already loaded — do nothing
	loadedKey = key
	revoke()
	images.value = []
	if (!jobId.value || !names.length) return
	const jid = jobId.value

	loadingPreviews.value = true
	try {
		// Fetch all pages concurrently (was sequential — 26 round-trips felt like a
		// re-scan). Cached pages resolve instantly.
		const blobs = await Promise.all(
			names.map(async name => {
				const ck = `${jid}::${name}`
				const hit = BLOB_CACHE.get(ck)
				if (hit) return hit
				// The dev fixture has no server side; it draws its own pages so this tab
				// still exercises the real fetch → object-URL → revoke path.
				if (USE_MOCK_ANALYSIS && jid === MOCK_JOB_ID) {
					const blob = await mockPreview(name)
					cachePut(ck, blob)
					return blob
				}
				try {
					const res = await Api.fileAnalysis.getPreview(jid, name)
					cachePut(ck, res.data)
					return res.data
				} catch (err) {
					message.error(getApiErrorMessage(err as ApiError) || `Failed to load preview ${name}`)
					return null
				}
			})
		)
		// A newer load may have started while we awaited — if so, discard ours.
		if (loadedKey !== key) return
		const urls = blobs.filter((b): b is Blob => b instanceof Blob).map(b => URL.createObjectURL(b))
		objectUrls = urls
		images.value = urls
	} finally {
		if (loadedKey === key) loadingPreviews.value = false
	}
}

// Watch only the derived KEY (a string), so unchanged name-sets don't re-trigger.
watch(() => `${jobId.value}::${(previewNames.value || []).join("|")}`, loadPreviews, { immediate: true })
onBeforeUnmount(revoke)
</script>

<style scoped>
.preview-grid {
	grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}
</style>
