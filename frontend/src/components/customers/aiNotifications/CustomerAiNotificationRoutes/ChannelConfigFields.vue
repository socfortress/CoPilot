<template>
	<div class="flex flex-col gap-1">
		<n-form-item v-for="field of fields" :key="field.key" :label="field.label" :path="`config.${field.key}`">
			<!-- string[] — one input per entry, add/remove inline -->
			<n-dynamic-input
				v-if="field.kind === 'string-array'"
				:value="asArray(field.key)"
				:on-create="() => ''"
				class="w-full"
				@update:value="v => set(field.key, v)"
			/>

			<n-checkbox
				v-else-if="field.kind === 'boolean'"
				:checked="Boolean(model[field.key])"
				@update:checked="v => set(field.key, v)"
			>
				{{ field.label }}
			</n-checkbox>

			<n-input-number
				v-else-if="field.kind === 'number'"
				:value="(model[field.key] as number | null) ?? null"
				clearable
				class="w-full"
				@update:value="v => set(field.key, v)"
			/>

			<n-input
				v-else
				:value="(model[field.key] as string | null) ?? null"
				:placeholder="field.placeholder"
				clearable
				@update:value="v => set(field.key, v)"
			/>

			<template v-if="field.description" #feedback>{{ field.description }}</template>
		</n-form-item>
	</div>
</template>

<script setup lang="ts">
import type { NotificationChannelDescriptor } from "@/types/notifications"
import { NCheckbox, NDynamicInput, NFormItem, NInput, NInputNumber } from "naive-ui"
import { computed } from "vue"

// Renders a channel's config form from the JSON Schema its provider advertises,
// for channels that have no hand-written block.
//
// This is a FALLBACK, not a replacement. Shuffle needs a searchable app picker
// that fetches a customer's orgs and then that org's authenticated apps; Resend
// needs `to` to appear only in static recipient mode. Neither is expressible in
// JSON Schema, and rendering them generically would be a downgrade. Channels
// whose config is genuinely a few flat fields — Teams is a webhook URL — get
// this for free and need no frontend work at all.

const props = defineProps<{
	descriptor: NotificationChannelDescriptor
	model: Record<string, unknown>
}>()

// The parent owns `config`. Emitting a key/value rather than mutating the prop
// keeps ownership in one place and satisfies vue/no-mutating-props.
const emit = defineEmits<{
	(e: "update", key: string, value: unknown): void
}>()

type FieldKind = "string" | "number" | "boolean" | "string-array"

interface RenderableField {
	key: string
	label: string
	kind: FieldKind
	description?: string
	placeholder?: string
}

interface SchemaNode {
	type?: string
	title?: string
	description?: string
	default?: unknown
	anyOf?: SchemaNode[]
	items?: SchemaNode
}

/**
 * Resolve a property's effective type.
 *
 * Pydantic renders `Optional[str]` as `anyOf: [{type: "string"}, {type: "null"}]`
 * rather than a plain type, so a renderer that only reads `.type` silently falls
 * through to a text input for every optional field — including numbers and
 * booleans. Unwrap to the first non-null branch.
 */
function resolveKind(node: SchemaNode): FieldKind {
	let resolved: SchemaNode = node
	if (node.anyOf?.length) {
		resolved = node.anyOf.find(n => n.type && n.type !== "null") ?? node.anyOf[0]
	}

	if (resolved.type === "array") {
		return resolved.items?.type === "string" ? "string-array" : "string"
	}
	if (resolved.type === "boolean") return "boolean"
	if (resolved.type === "integer" || resolved.type === "number") return "number"
	return "string"
}

/** "webhook_url" -> "Webhook url", when the schema supplies no title. */
function humanize(key: string): string {
	const spaced = key.replace(/_/g, " ")
	return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

const fields = computed<RenderableField[]>(() => {
	const properties = (props.descriptor.config_schema?.properties ?? {}) as Record<string, SchemaNode>
	return Object.entries(properties).map(([key, node]) => ({
		key,
		label: node.title || humanize(key),
		kind: resolveKind(node),
		description: node.description,
		placeholder: typeof node.default === "string" && node.default ? String(node.default) : undefined
	}))
})

function asArray(key: string): string[] {
	const value = props.model[key]
	return Array.isArray(value) ? (value as string[]) : []
}

function set(key: string, value: unknown) {
	emit("update", key, value)
}
</script>
