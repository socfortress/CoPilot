<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAiAnalystIoc())">
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
import { ref, watch } from "vue"
import IocDetails from "@/components/aiAnalyst/IocDetails.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeAiAnalystIoc } = useNavigation()

const BackIcon = "carbon:arrow-left"
const ioc = ref<AiAnalystIoc | null>(null)

const iocId = useRouteIdParam("id")

watch(iocId, () => {
	ioc.value = null
})
</script>
