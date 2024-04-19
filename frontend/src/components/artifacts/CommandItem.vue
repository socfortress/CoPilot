<template>
	<div class="command-item flex flex-col">
		<div class="header-box flex justify-between">
			<div class="status">
				Complete:
				<strong class="font-mono" :class="{ success: command.Complete + '' === 'true' }">
					{{ command.Complete }}
				</strong>
			</div>
			<div class="code">
				Code:
				<strong class="font-mono">{{ command.ReturnCode }}</strong>
			</div>
		</div>
		<div class="main-box">
			<div class="output stdout" v-if="command.Stdout">
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
			<div class="output stderr" v-if="command.Stderr">
				<label class="flex items-center">
					<Icon :name="DangerIcon" class="mr-1"></Icon>
					Stderr
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
	</div>
</template>

<script setup lang="ts">
import { NInput } from "naive-ui"
import type { CommandResult } from "@/types/artifacts.d"
import Icon from "@/components/common/Icon.vue"

const { command } = defineProps<{ command: CommandResult }>()

const DangerIcon = "majesticons:exclamation-line"
</script>

<style lang="scss" scoped>
.command-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	max-width: 100%;
	overflow: hidden;

	.header-box {
		padding: 16px 20px;
		font-family: var(--font-family-mono);
		font-size: 14px;
		border-bottom: var(--border-small-100);
		.status {
			strong {
				color: var(--warning-color);
				&.success {
					color: var(--primary-color);
				}
			}
		}
	}
	.main-box {
		.output {
			margin-top: 20px;

			label {
				padding: 0px 20px;
				line-height: 1;
			}

			.n-input {
				margin-top: 8px;
				border-radius: 0;

				background-color: var(--n-color) !important;

				:deep() {
					.n-input__border,
					.n-input__state-border {
						display: none;
					}
				}
			}

			&.stderr {
				label {
					color: var(--warning-color);
				}
			}
		}
	}
}
</style>
