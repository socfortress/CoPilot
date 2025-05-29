<template>
	<CardEntity>
		<template #headerMain>
			Complete:
			<strong class="font-mono" :class="{ 'text-success': `${command.Complete}` === 'true' }">
				{{ command.Complete }}
			</strong>
		</template>
		<template #headerExtra>
			Code:
			<strong class="font-mono">{{ command.ReturnCode }}</strong>
		</template>

		<template #mainExtra>
			<div class="flex flex-col gap-4">
				<div v-if="command.Stdout" class="flex flex-col gap-2">
					<label>Stdout</label>
					<n-input
						:value="command.Stdout"
						type="textarea"
						readonly
						placeholder="Empty"
						size="large"
						:autosize="{
							minRows: 3
						}"
					/>
				</div>
				<div v-if="command.Stderr" class="flex flex-col gap-2">
					<label class="text-error flex items-center gap-2 leading-none">
						<Icon :name="DangerIcon" />
						<span>Stderr</span>
					</label>
					<n-input
						:value="command.Stderr"
						type="textarea"
						readonly
						placeholder="Empty"
						size="large"
						:autosize="{
							minRows: 3
						}"
					/>
				</div>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { CommandResult } from "@/types/artifacts.d"
import { NInput } from "naive-ui"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const { command } = defineProps<{ command: CommandResult }>()

const DangerIcon = "majesticons:exclamation-line"
</script>
