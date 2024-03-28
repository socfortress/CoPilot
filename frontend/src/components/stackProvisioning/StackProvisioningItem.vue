<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between gap-4">
			<div class="name">{{ contentPack.name }}</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="description">{{ contentPack.description }}</div>
			<div class="actions-box">
				<n-button :loading="loadingProvision" type="success" secondary @click="provision(contentPack.name)">
					<template #icon><Icon :name="DeployIcon"></Icon></template>
					Deploy
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center gap-4">
			<div class="actions-box">
				<n-button
					:loading="loadingProvision"
					type="success"
					secondary
					size="small"
					@click="provision(contentPack.name)"
				>
					<template #icon><Icon :name="DeployIcon"></Icon></template>
					Deploy
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { NButton, useMessage } from "naive-ui"
import Api from "@/api"
import type { AvailableContentPack } from "@/types/stackProvisioning.d"

const emit = defineEmits<{
	(e: "provisioned"): void
}>()

const { contentPack } = defineProps<{ contentPack: AvailableContentPack }>()

const DeployIcon = "mdi:package-variant-closed-check"
const loadingProvision = ref(false)
const message = useMessage()

function provision(contentPackName: string) {
	loadingProvision.value = true

	Api.stackProvisioning
		.provisionContentPack(contentPackName)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Content Pack Provisioned Successfully")
				emit("provisioned")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingProvision.value = false
		})
}
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-secondary-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-size: 13px;

		.name {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
		}
	}
	.main-box {
		.description {
			word-break: break-word;
		}
	}

	.footer-box {
		display: none;
		font-size: 13px;
		margin-top: 10px;
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 450px) {
		.main-box {
			.actions-box {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
