<template>
	<n-drawer
		:show="drawerId !== null"
		:width="drawerWidth"
		placement="right"
		auto-focus
		data-testid="talon-memory-detail"
		@update:show="value => !value && close()"
	>
		<n-drawer-content closable :native-scrollbar="false" title="Memory">
			<div v-if="loading" class="flex justify-center py-10" data-testid="talon-memory-detail-loading">
				<n-spin size="small" />
			</div>
			<MemoryProblem v-else-if="problem" :state="problem" @retry="load()" />
			<div v-else-if="drawer" class="flex flex-col gap-4" data-testid="talon-memory-detail-body">
				<dl class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
					<dt class="text-secondary">Room</dt>
					<dd data-testid="talon-memory-detail-room">
						<bdi>{{ roomText(drawer.room, drawer.room_name) }}</bdi>
					</dd>
					<dt class="text-secondary">Source</dt>
					<dd data-testid="talon-memory-detail-source">
						{{ sourceLabel(drawer.source) }}
						<template v-if="drawer.durable">· durable</template>
					</dd>
					<dt class="text-secondary">Filed</dt>
					<dd>{{ formatTime(drawer.filed_at) }}</dd>
					<template v-if="drawer.source_ref">
						<dt class="text-secondary">From</dt>
						<dd class="flex flex-wrap gap-x-3 gap-y-1" data-testid="talon-memory-detail-links">
							<RouterLink
								v-if="drawer.source_ref.job_id"
								:to="{ name: 'AiAnalystJob', params: { id: drawer.source_ref.job_id } }"
								class="text-primary"
								data-testid="talon-memory-detail-job"
							>
								Investigation
								<span class="font-mono">{{ drawer.source_ref.job_id }}</span>
							</RouterLink>
							<RouterLink
								v-if="drawer.source_ref.alert_id"
								:to="{
									name: 'IncidentManagement-Alert',
									params: { id: String(drawer.source_ref.alert_id) }
								}"
								class="text-primary"
								data-testid="talon-memory-detail-alert"
							>
								Alert #{{ drawer.source_ref.alert_id }}
							</RouterLink>
						</dd>
					</template>
					<dt class="text-secondary">Drawer</dt>
					<dd class="font-mono text-xs break-all">
						<bdi>{{ drawer.drawer_id }}</bdi>
					</dd>
				</dl>

				<n-alert
					v-if="hidden"
					type="warning"
					:bordered="false"
					title="Not used by new investigations"
					data-testid="talon-memory-detail-hidden"
				>
					<p v-if="drawer.why_hidden">
						<bdi>{{ drawer.why_hidden }}</bdi>
					</p>
					<p class="text-secondary mt-1 text-xs">
						A lesson learnt while testing is kept out of investigations. Testing is never a reason to lower
						an alert's severity: simulated attacks are investigated as real ones.
					</p>
				</n-alert>

				<section aria-label="What Talon remembers" class="border-default rounded-lg border p-3">
					<!-- Markdown-it with HTML off (raw HTML shows as text), images as links, never loaded. -->
					<Markdown
						v-if="drawer.content"
						:source="drawer.content"
						no-images
						breaks
						data-testid="talon-memory-detail-content"
					/>
					<p v-else class="text-tertiary text-sm">Talon sent no content for this memory.</p>
				</section>

				<n-alert v-if="forgetFailure" type="error" :bordered="false" data-testid="talon-memory-forget-error">
					<bdi>{{ forgetFailure }}</bdi>
				</n-alert>

				<div class="flex flex-wrap items-center justify-between gap-2">
					<p v-if="!forgettable" class="text-tertiary text-xs" data-testid="talon-memory-not-forgettable">
						<bdi>{{ drawer.why_not_forgettable ?? NOT_FORGETTABLE_TEXT }}</bdi>
					</p>
					<span v-else />
					<n-button
						v-if="forgettable"
						type="error"
						secondary
						size="small"
						data-testid="talon-memory-forget"
						@click="confirming = true"
					>
						<template #icon><Icon name="carbon:trash-can" :size="14" /></template>
						Forget…
					</n-button>
				</div>
			</div>
		</n-drawer-content>

		<n-modal
			v-model:show="confirming"
			preset="card"
			title="Forget this memory?"
			:style="{ maxWidth: 'min(480px, 94vw)' }"
			:mask-closable="!forgetting"
			:closable="!forgetting"
			segmented
			data-testid="talon-memory-forget-confirm"
		>
			<div v-if="drawer" class="flex flex-col gap-2 text-sm">
				<p>
					Talon will stop using this {{ sourceLabel(drawer.source).toLowerCase() }} lesson for
					<b>
						<bdi>{{ customerCode }}</bdi>
					</b>
					. This can't be undone, and the forget is recorded in the audit log.
				</p>
				<p class="text-secondary">
					It doesn't change reports or reviews already written, and an analyst can teach Talon the lesson
					again.
				</p>
			</div>
			<template #footer>
				<div class="flex justify-end gap-2">
					<n-button
						:disabled="forgetting"
						data-testid="talon-memory-forget-cancel"
						@click="confirming = false"
					>
						Cancel
					</n-button>
					<n-button
						type="error"
						:loading="forgetting"
						:disabled="forgetting"
						data-testid="talon-memory-forget-confirm-button"
						@click="forget()"
					>
						Forget
					</n-button>
				</div>
			</template>
		</n-modal>
	</n-drawer>
</template>

<script setup lang="ts">
// One memory, in a side drawer: where it came from (links to the investigation's job page and the
// alert), why it is hidden from investigations, its markdown (through `Markdown`, markdown-it with
// raw HTML off and images never loaded; never bound as HTML), and Forget only when the memory may be
// forgotten (`canForget`: talon-analyst says so and it is a one-off review or chat remember lesson).
// Forget asks for confirmation in a modal, never a browser dialog.
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonMemoryDrawer } from "@/types/talonMemory"
import { useWindowSize } from "@vueuse/core"
import { NAlert, NButton, NDrawer, NDrawerContent, NModal, NSpin } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { RouterLink } from "vue-router"
import Api from "@/api"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { formatTime } from "../health/health"
import { canForget, problemState, roomText, sourceLabel } from "./memory"
import MemoryProblem from "./MemoryProblem.vue"

const { customerCode, drawerId } = defineProps<{ customerCode: string; drawerId: string | null }>()
const emit = defineEmits<{
	(e: "close"): void
	(e: "forgotten", drawerId: string): void
}>()

const NOT_FORGETTABLE_TEXT =
	"Only one-off review lessons and chat remember lessons can be forgotten, never an investigation's own record or a durable lesson."

const { width } = useWindowSize()
const drawerWidth = computed(() => Math.min(720, Math.round(width.value * 0.94)))

const drawer = ref<TalonMemoryDrawer | null>(null)
const failure = ref<TalonMemoryFailure | null>(null)
const loading = ref(false)
const confirming = ref(false)
const forgetting = ref(false)
const forgetFailure = ref<string | null>(null)
let controller: AbortController | null = null

const problem = computed(() => problemState(failure.value))
const forgettable = computed(() => canForget(drawer.value))
const hidden = computed(
	() => !!drawer.value && (drawer.value.testing_hidden === true || drawer.value.visible_to_investigations === false)
)

async function load() {
	controller?.abort()
	drawer.value = null
	failure.value = null
	forgetFailure.value = null
	if (drawerId === null) return
	const own = new AbortController()
	controller = own
	loading.value = true
	try {
		const { data } = await Api.talonMemory.getDrawer(customerCode, drawerId, own.signal)
		if (controller !== own) return
		drawer.value = data
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		failure.value = memoryFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

async function forget() {
	if (!drawer.value || forgetting.value) return
	const id = drawer.value.drawer_id
	forgetting.value = true
	forgetFailure.value = null
	try {
		await Api.talonMemory.forgetDrawer(customerCode, id)
		confirming.value = false
		emit("forgotten", id)
		emit("close")
	} catch (err) {
		const why = memoryFailure(err)
		confirming.value = false
		forgetFailure.value = why.code === "not_found" ? "Talon no longer has this memory." : why.detail
	} finally {
		forgetting.value = false
	}
}

function close() {
	if (forgetting.value) return
	confirming.value = false
	emit("close")
}

watch(() => [customerCode, drawerId], load, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>
