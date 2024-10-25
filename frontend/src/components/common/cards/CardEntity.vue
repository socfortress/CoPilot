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
			border-top: var(--border-small-050);
		}

		.footer-box {
			border-top: var(--border-small-050);
			font-size: 13px;
			background-color: var(--bg-secondary-color);
		}

		.main-box,
		.extra-box,
		.footer-box {
			@apply gap-3 px-5 py-3;
		}

		.main-box {
			.header-box {
				@apply gap-3;
			}
		}
	}

	&.card-size-small {
		.card-entity-wrapper {
			.main-box,
			.extra-box,
			.footer-box {
				@apply gap-2 px-3 py-2;
			}

			.main-box {
				.header-box {
					@apply gap-2;
				}
			}
		}
	}

	&.card-size-large {
		.card-entity-wrapper {
			.main-box,
			.extra-box,
			.footer-box {
				@apply gap-6 px-8 py-6;
			}

			.main-box {
				.header-box {
					@apply gap-6;
				}
			}
		}
	}

	&.clickable {
		@apply cursor-pointer;
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
		border: var(--border-small-100);

		.footer-box {
			background-color: var(--bg-body);
		}
	}

	&.card-status-success {
		background-color: var(--success-005-color);
		border-color: var(--success-030-color);
	}

	&.card-status-warning {
		background-color: var(--warning-005-color);
		border-color: var(--warning-030-color);
	}

	&.card-status-error {
		background-color: var(--error-005-color);
		border-color: var(--error-030-color);
	}

	&.hoverable {
		&:not(.disabled) {
			&:hover {
				border-color: var(--primary-040-color);
			}
		}
	}

	&.highlighted {
		background-color: var(--primary-005-color);
		border-color: var(--primary-030-color);

		&:not(.disabled) {
			&:hover {
				box-shadow: 0px 0px 0px 1px var(--primary-color);
			}
		}
	}

	&.disabled {
		@apply cursor-not-allowed;

		.card-entity-wrapper {
			@apply opacity-70;
		}
	}
}
</style>
