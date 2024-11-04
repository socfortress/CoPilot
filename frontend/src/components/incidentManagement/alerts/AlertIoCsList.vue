<template>
	<div>
		<n-collapse-transition :show="!showForm">
			<n-button v-if="iocs.length" :loading="submitting" type="primary" @click="openForm()">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				Create IoC
			</n-button>
		</n-collapse-transition>

		<CollapseKeepAlive :show="showForm">
			<div class="flex flex-col gap-2">
				<AlertIoCsForm
					v-model:loading="submitting"
					:alert-id
					@mounted="formCTX = $event"
					@submitted="addIoc($event)"
				>
					<template #additionalActions>
						<n-button secondary :disabled="submitting" @click="closeForm()">Close</n-button>
					</template>
				</AlertIoCsForm>
			</div>
		</CollapseKeepAlive>

		<div class="mt-3 flex flex-col gap-2">
			<template v-if="iocs.length">
				<AlertIoCItem v-for="ioc of iocs" :key="ioc.id" :ioc :alert-id embedded @deleted="delIoc(ioc)" />
			</template>
			<template v-else>
				<n-collapse-transition :show="!showForm">
					<n-empty v-if="!loading" class="min-h-48">
						<div class="flex flex-col items-center gap-4">
							<p>No IoCs found</p>
							<n-button type="primary" :loading="submitting" @click="openForm()">
								<template #icon>
									<Icon :name="AddIcon" />
								</template>
								Create an IoCs
							</n-button>
						</div>
					</n-empty>
				</n-collapse-transition>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertIOC } from "@/types/incidentManagement/alerts.d"
import CollapseKeepAlive from "@/components/common/CollapseKeepAlive.vue"
import Icon from "@/components/common/Icon.vue"
import _get from "lodash/get"
import _trim from "lodash/trim"
import { NButton, NCollapseTransition, NEmpty } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import AlertIoCItem from "./AlertIoCItem.vue"
import AlertIoCsForm from "./AlertIoCsForm.vue"

const props = defineProps<{ iocs: AlertIOC[]; alertId: number }>()
const emit = defineEmits<{
	(e: "updated", value: AlertIOC[]): void
}>()

const { iocs, alertId } = toRefs(props)

const AddIcon = "carbon:add-alt"
const iocsList = ref<AlertIOC[]>(iocs.value)
const showForm = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const loading = computed(() => submitting.value || deleting.value)
const formCTX = ref<{ reset: (force?: boolean) => void } | null>(null)

function openForm() {
	showForm.value = true
}

function closeForm(doReset?: boolean) {
	showForm.value = false
	if (doReset) {
		formCTX.value?.reset(true)
	}
}

function delIoc(ioc: AlertIOC) {
	iocsList.value = iocsList.value.filter(o => o.id !== ioc.id)
	emit("updated", iocsList.value)
}

function addIoc(ioc: AlertIOC) {
	iocsList.value.push(ioc)
	closeForm(true)
	emit("updated", iocsList.value)
}
</script>
