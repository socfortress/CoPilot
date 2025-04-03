<template>
	<n-card
		class="card-entity"
		content-class="!p-0"
		:class="[
			`card-size-${size}`,
			`card-status-${status}`,
			{ embedded, highlighted, clickable, hoverable, disabled }
		]"
	>
		<n-spin :show="loading" :description="loadingDescription">
			<div class="card-entity-wrapper flex flex-col">
				<div class="main-box flex flex-col">
					<div v-if="$slots.header" class="header-box">
						<slot name="header" />
					</div>

					<div
						v-if="!$slots.header && ($slots.headerMain || $slots.headerExtra)"
						class="header-box flex flex-wrap items-center justify-between"
					>
						<div>
							<slot name="headerMain" />
						</div>
						<div>
							<slot name="headerExtra" />
						</div>
					</div>

					<div v-if="$slots.default" class="content-box">
						<slot name="default" />
					</div>
				</div>

				<div v-if="$slots.mainExtra" class="extra-box">
					<slot name="mainExtra" />
				</div>

				<div v-if="$slots.footer" class="footer-box">
					<slot name="footer" />
				</div>

				<div
					v-if="!$slots.footer && ($slots.footerMain || $slots.footerExtra)"
					class="footer-box flex flex-wrap items-start justify-between"
				>
					<div>
						<slot name="footerMain" />
					</div>
					<div>
						<slot name="footerExtra" />
					</div>
				</div>
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NSpin } from "naive-ui"

const { size, status, embedded, highlighted, clickable, hoverable, disabled, loading, loadingDescription } =
	defineProps<{
		size?: "medium" | "small" | "large"
		status?: "success" | "warning" | "error"
		embedded?: boolean
		highlighted?: boolean
		clickable?: boolean
		hoverable?: boolean
		disabled?: boolean
		loading?: boolean
		loadingDescription?: string
	}>()
</script>

<style lang="scss" scoped>
.card-entity {
	transition: all 0.2s var(--bezier-ease);
	overflow: hidden;

	.card-entity-wrapper {
		.main-box {
			.header-box {
				font-family: var(--font-family-mono);
				font-size: 13px;
				color: var(--fg-secondary-color);

				:deep(.n-button) {
					font-family: var(--font-family);
				}
			}
			.content-box {
				word-break: break-word;
			}
		}

		.extra-box {
			border-top: 1px solid var(--border-color);
		}

		.footer-box {
			border-top: 1px solid var(--border-color);
			font-size: 13px;
			background-color: var(--bg-secondary-color);
		}

		.main-box,
		.extra-box,
		.footer-box {
			gap: calc(var(--spacing) * 3);
			padding: calc(var(--spacing) * 4);
		}

		.main-box {
			.header-box {
				gap: calc(var(--spacing) * 3);
			}
		}
	}

	&.card-size-small {
		.card-entity-wrapper {
			.main-box,
			.extra-box,
			.footer-box {
				gap: calc(var(--spacing) * 2);
				padding: calc(var(--spacing) * 3);
			}

			.main-box {
				.header-box {
					gap: calc(var(--spacing) * 2);
				}
			}
		}
	}

	&.card-size-large {
		.card-entity-wrapper {
			.main-box,
			.extra-box,
			.footer-box {
				gap: calc(var(--spacing) * 6);
				padding: calc(var(--spacing) * 6);
			}

			.main-box {
				.header-box {
					gap: calc(var(--spacing) * 6);
				}
			}
		}
	}

	&.clickable {
		cursor: pointer;
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
		border: 1px solid var(--border-color);

		.footer-box {
			background-color: var(--bg-body-color);
		}
	}

	&.card-status-success {
		background-color: rgba(var(--success-color-rgb) / 0.05);
		border-color: rgba(var(--success-color-rgb) / 0.3);
	}

	&.card-status-warning {
		background-color: rgba(var(--warning-color-rgb) / 0.05);
		border-color: rgba(var(--warning-color-rgb) / 0.3);
	}

	&.card-status-error {
		background-color: rgba(var(--error-color-rgb) / 0.05);
		border-color: rgba(var(--error-color-rgb) / 0.3);
	}

	&.hoverable {
		&:not(.disabled) {
			&:hover {
				border-color: rgba(var(--primary-color-rgb) / 0.4);
			}
		}
	}

	&.highlighted {
		background-color: rgba(var(--primary-color-rgb) / 0.05);
		border-color: rgba(var(--primary-color-rgb) / 0.3);

		&:not(.disabled) {
			&:hover {
				box-shadow: 0px 0px 0px 1px var(--primary-color);
			}
		}
	}

	&.disabled {
		cursor: not-allowed;

		.card-entity-wrapper {
			opacity: 70%;
		}
	}
}
</style>
