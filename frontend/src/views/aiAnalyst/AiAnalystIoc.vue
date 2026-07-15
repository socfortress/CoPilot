<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeAiAnalystIoc()">
			<template v-if="ioc" #title>
				<span class="truncate font-mono text-lg font-semibold">{{ ioc.ioc_value }}</span>
			</template>
			<template v-if="ioc" #meta>
				<span class="text-secondary font-mono text-sm">#{{ ioc.id }}</span>
				<span class="text-secondary text-sm">{{ ioc.ioc_type }}</span>
			</template>
		</DetailPageHeader>

		<IocDetails v-if="iocId != null" :ioc-id :embedded="false" @loaded="ioc = $event" />
		<n-empty v-else description="Invalid IOC ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystIoc } from "@/types/ai-analyst"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import IocDetails from "@/components/aiAnalyst/IocDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeAiAnalystIoc } = useNavigation()

const ioc = ref<AiAnalystIoc | null>(null)

const iocId = useRouteIdParam("id")

watch(iocId, () => {
	ioc.value = null
})
</script>
