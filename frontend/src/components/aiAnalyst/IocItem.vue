<template>
	<IocDetails :ioc>
		<template #footerExtra>
			<EntityDetailsButton
				size="tiny"
				:order="['open']"
				open-show-label
				:url="routeAiAnalystIoc(ioc.id).fullUrl()"
			/>
		</template>
	</IocDetails>
</template>

<script setup lang="ts">
import type { AiAnalystIoc } from "@/types/ai-analyst"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import { useNavigation } from "@/composables/useNavigation"
import IocDetails from "./IocDetails.vue"

const { ioc } = defineProps<{ ioc: AiAnalystIoc }>()

const { routeAiAnalystIoc } = useNavigation()
</script>
