<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="router.push({ name: 'Audit' })">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to audit
		</n-button>

		<AuditDetails v-if="entryId != null" :entry-id="entryId" :embedded="false" />
		<n-empty v-else description="Invalid audit entry ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import AuditDetails from "@/components/audit/AuditDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const entryId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})
</script>
