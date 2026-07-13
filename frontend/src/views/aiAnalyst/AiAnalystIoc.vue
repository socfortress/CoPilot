<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="ioc" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate font-mono text-lg font-semibold">{{ ioc.ioc_value }}</span>
				<span class="text-secondary font-mono text-sm">#{{ ioc.id }}</span>
				<span class="text-secondary text-sm">{{ ioc.ioc_type }}</span>
			</div>
		</div>

		<IocDetails v-if="iocId != null" :ioc-id :embedded="false" @loaded="ioc = $event" />
		<n-empty v-else description="Invalid IOC ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystIoc } from "@/types/ai-analyst"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import IocDetails from "@/components/aiAnalyst/IocDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"
const ioc = ref<AiAnalystIoc | null>(null)

const iocId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})

watch(iocId, () => {
	ioc.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "AiAnalyst" })
}
</script>
