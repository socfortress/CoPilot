<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Agents
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<button
							@click="refreshAlerts"
							:disabled="loading"
							class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm leading-4 font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:opacity-50"
						>
							<svg
								class="mr-2 h-4 w-4"
								:class="{ 'animate-spin': loading }"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
								></path>
							</svg>
							Refresh
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Stats Cards -->
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500">
									<svg class="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									</svg>
								</div>
							</div>
							<div class="ml-5 w-0 flex-1">
								<dl>
									<dt class="truncate text-sm font-medium text-gray-500">Total Alerts</dt>
									<dd class="text-lg font-medium text-gray-900">{{ stats.total }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>

				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="flex h-8 w-8 items-center justify-center rounded-md bg-red-500">
									<svg class="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path
											fill-rule="evenodd"
											d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
											clip-rule="evenodd"
										></path>
									</svg>
								</div>
							</div>
							<div class="ml-5 w-0 flex-1">
								<dl>
									<dt class="truncate text-sm font-medium text-gray-500">Open</dt>
									<dd class="text-lg font-medium text-gray-900">{{ stats.open }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>

				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="flex h-8 w-8 items-center justify-center rounded-md bg-yellow-500">
									<svg class="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path
											fill-rule="evenodd"
											d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
											clip-rule="evenodd"
										></path>
									</svg>
								</div>
							</div>
							<div class="ml-5 w-0 flex-1">
								<dl>
									<dt class="truncate text-sm font-medium text-gray-500">In Progress</dt>
									<dd class="text-lg font-medium text-gray-900">{{ stats.in_progress }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>

				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class="flex h-8 w-8 items-center justify-center rounded-md bg-green-500">
									<svg class="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path
											fill-rule="evenodd"
											d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
											clip-rule="evenodd"
										></path>
									</svg>
								</div>
							</div>
							<div class="ml-5 w-0 flex-1">
								<dl>
									<dt class="truncate text-sm font-medium text-gray-500">Closed</dt>
									<dd class="text-lg font-medium text-gray-900">{{ stats.closed }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Filters -->
			<div class="mb-6 rounded-lg bg-white shadow">
				<div class="px-4 py-5 sm:p-6">
					<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
						<div>
							<label for="status-filter" class="block text-sm font-medium text-gray-700">Status</label>
							<select
								id="status-filter"
								v-model="filters.status"
								@change="applyFilters"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="">All Statuses</option>
								<option value="open">Open</option>
								<option value="in_progress">In Progress</option>
								<option value="closed">Closed</option>
							</select>
						</div>
						<div>
							<label for="source-filter" class="block text-sm font-medium text-gray-700">Source</label>
							<select
								id="source-filter"
								v-model="filters.source"
								@change="applyFilters"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="">All Sources</option>
								<option v-for="source in availableSources" :key="source" :value="source">
									{{ source }}
								</option>
							</select>
						</div>
						<div>
							<label for="asset-filter" class="block text-sm font-medium text-gray-700">Asset</label>
							<select
								id="asset-filter"
								v-model="filters.asset"
								@change="applyFilters"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="">All Assets</option>
								<option v-for="asset in availableAssets" :key="asset" :value="asset">
									{{ asset }}
								</option>
							</select>
						</div>
					</div>
				</div>
			</div>

			<!-- Alerts List -->
			<div class="overflow-hidden bg-white shadow sm:rounded-md">
				<div v-if="loading" class="px-4 py-5 text-center sm:p-6">
					<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
					<p class="mt-2 text-sm text-gray-500">Loading alerts...</p>
				</div>

				<div v-else-if="error" class="px-4 py-5 text-center sm:p-6">
					<div class="mb-2 text-red-500">
						<svg class="mx-auto h-8 w-8" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
								clip-rule="evenodd"
							></path>
						</svg>
					</div>
					<p class="text-sm text-red-600">{{ error }}</p>
					<button
						@click="loadAlerts"
						class="mt-2 inline-flex items-center rounded-md border border-transparent bg-indigo-100 px-3 py-2 text-sm leading-4 font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
					>
						Try Again
					</button>
				</div>

				<ul v-else-if="alerts.length > 0" role="list" class="divide-y divide-gray-200">
					<li v-for="alert in alerts" :key="alert.id" class="px-4 py-4 hover:bg-gray-50 sm:px-6">
						<div class="flex items-center justify-between">
							<div class="flex items-center">
								<div class="flex-shrink-0">
									<span
										class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': alert.status === 'OPEN',
											'bg-yellow-100 text-yellow-800': alert.status === 'IN_PROGRESS',
											'bg-green-100 text-green-800': alert.status === 'CLOSED'
										}"
									>
										{{ alert.status.replace("_", " ").toUpperCase() }}
									</span>
								</div>
								<div class="ml-4">
									<div class="text-sm font-medium text-gray-900">
										{{ alert.alert_name }}
									</div>
									<div class="text-sm text-gray-500">
										<span v-if="alert.assets.length > 0">
											Asset: {{ alert.assets[0].asset_name }}
										</span>
										<span v-else-if="alert.asset_name">Asset: {{ alert.asset_name }}</span>
										| Source: {{ alert.source }}
									</div>
									<div class="text-xs text-gray-400">
										{{ formatDate(alert.alert_creation_time) }}
									</div>
								</div>
							</div>
							<div class="flex items-center space-x-2">
								<select
									:value="alert.status"
									@change="updateAlertStatus(alert.id, ($event.target as HTMLSelectElement).value)"
									class="rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
									:disabled="updatingStatus === alert.id"
								>
									<option value="OPEN">Open</option>
									<option value="IN_PROGRESS">In Progress</option>
									<option value="CLOSED">Closed</option>
								</select>
								<button
									@click="viewAlert(alert)"
									class="inline-flex items-center rounded border border-transparent bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									View Details
								</button>
							</div>
						</div>
						<div v-if="alert.alert_description" class="mt-2 text-sm text-gray-600">
							{{ alert.alert_description }}
						</div>
					</li>
				</ul>

				<div v-else class="px-4 py-5 text-center sm:p-6">
					<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
						></path>
					</svg>
					<h3 class="mt-2 text-sm font-medium text-gray-900">No alerts found</h3>
					<p class="mt-1 text-sm text-gray-500">No security alerts match your current filters.</p>
				</div>
			</div>

			<!-- Pagination -->
			<div
				v-if="alerts.length > 0"
				class="mt-6 flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6"
			>
				<div class="flex flex-1 justify-between sm:hidden">
					<button
						@click="previousPage"
						:disabled="currentPage <= 1"
						class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
					>
						Previous
					</button>
					<button
						@click="nextPage"
						:disabled="currentPage >= totalPages"
						class="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
					>
						Next
					</button>
				</div>
				<div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
					<div>
						<p class="text-sm text-gray-700">
							Showing
							<span class="font-medium">{{ (currentPage - 1) * pageSize + 1 }}</span>
							to
							<span class="font-medium">{{ Math.min(currentPage * pageSize, stats.total) }}</span>
							of
							<span class="font-medium">{{ stats.total }}</span>
							results
						</p>
					</div>
					<div>
						<nav class="relative z-0 inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
							<button
								@click="previousPage"
								:disabled="currentPage <= 1"
								class="relative inline-flex items-center rounded-l-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
							>
								Previous
							</button>
							<button
								@click="nextPage"
								:disabled="currentPage >= totalPages"
								class="relative inline-flex items-center rounded-r-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
							>
								Next
							</button>
						</nav>
					</div>
				</div>
			</div>
		</div>

		<!-- Alert Details Modal -->
		<div
			v-if="selectedAlert"
			class="bg-opacity-50 fixed inset-0 z-50 h-full w-full overflow-y-auto bg-gray-600"
			@click="closeModal"
		>
			<div
				class="relative top-10 mx-auto max-h-screen w-11/12 overflow-y-auto rounded-md border bg-white p-5 shadow-lg md:w-4/5 lg:w-3/4"
				@click.stop
			>
				<div class="mb-4 flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900">Alert Details</h3>
					<button @click="closeModal" class="text-gray-400 hover:text-gray-600">
						<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				</div>

				<div class="space-y-6">
					<!-- Basic Alert Information -->
					<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
						<div>
							<label class="block text-sm font-medium text-gray-700">Alert Name</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedAlert.alert_name }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Status</label>
							<span
								class="mt-1 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
								:class="{
									'bg-red-100 text-red-800': selectedAlert.status === 'OPEN',
									'bg-yellow-100 text-yellow-800': selectedAlert.status === 'IN_PROGRESS',
									'bg-green-100 text-green-800': selectedAlert.status === 'CLOSED'
								}"
							>
								{{ selectedAlert.status.replace("_", " ").toUpperCase() }}
							</span>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Source</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedAlert.source }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Customer</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedAlert.customer_code }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Created</label>
							<p class="mt-1 text-sm text-gray-900">
								{{ formatDate(selectedAlert.alert_creation_time) }}
							</p>
						</div>
						<div v-if="selectedAlert.assigned_to">
							<label class="block text-sm font-medium text-gray-700">Assigned To</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedAlert.assigned_to }}</p>
						</div>
					</div>

					<div v-if="selectedAlert.alert_description">
						<label class="block text-sm font-medium text-gray-700">Description</label>
						<p class="mt-1 text-sm whitespace-pre-wrap text-gray-900">
							{{ selectedAlert.alert_description }}
						</p>
					</div>

					<!-- Assets Section -->
					<div v-if="selectedAlert.assets && selectedAlert.assets.length > 0">
						<label class="mb-2 block text-sm font-medium text-gray-700">Assets</label>
						<div class="rounded-lg bg-gray-50 p-4">
							<div
								v-for="asset in selectedAlert.assets"
								:key="asset.id"
								class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
							>
								<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-3">
									<div>
										<span class="font-medium">Asset Name:</span>
										{{ asset.asset_name }}
									</div>
									<div>
										<span class="font-medium">Agent ID:</span>
										{{ asset.agent_id }}
									</div>
									<div v-if="asset.velociraptor_id">
										<span class="font-medium">Velociraptor ID:</span>
										{{ asset.velociraptor_id }}
									</div>
									<div>
										<span class="font-medium">Index:</span>
										{{ asset.index_name }}
									</div>
									<div>
										<span class="font-medium">Index ID:</span>
										{{ asset.index_id.substring(0, 20) }}...
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Fallback for legacy asset_name -->
					<div v-else-if="selectedAlert.asset_name">
						<label class="block text-sm font-medium text-gray-700">Asset</label>
						<p class="mt-1 text-sm text-gray-900">{{ selectedAlert.asset_name }}</p>
					</div>

					<!-- Tags Section -->
					<div v-if="selectedAlert.tags && selectedAlert.tags.length > 0">
						<label class="block text-sm font-medium text-gray-700">Tags</label>
						<div class="mt-1 flex flex-wrap gap-2">
							<span
								v-for="tag in selectedAlert.tags"
								:key="tag.id"
								class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
							>
								{{ tag.tag }}
							</span>
						</div>
					</div>

					<!-- Legacy Tags (for backward compatibility) -->
					<div v-else-if="selectedAlert.tag && selectedAlert.tag.length > 0">
						<label class="block text-sm font-medium text-gray-700">Tags</label>
						<div class="mt-1 flex flex-wrap gap-2">
							<span
								v-for="tag in selectedAlert.tag"
								:key="tag"
								class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
							>
								{{ tag }}
							</span>
						</div>
					</div>

					<!-- Linked Cases Section -->
					<div v-if="selectedAlert.linked_cases && selectedAlert.linked_cases.length > 0">
						<label class="mb-2 block text-sm font-medium text-gray-700">Linked Cases</label>
						<div class="rounded-lg bg-gray-50 p-4">
							<div
								v-for="linkedCase in selectedAlert.linked_cases"
								:key="linkedCase.id"
								class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<h4 class="text-sm font-medium text-gray-900">{{ linkedCase.case_name }}</h4>
										<p class="mt-1 text-xs text-gray-600">{{ linkedCase.case_description }}</p>
										<div class="mt-2 flex items-center space-x-4 text-xs text-gray-500">
											<span>Case #{{ linkedCase.id }}</span>
											<span>Created: {{ formatDate(linkedCase.case_creation_time) }}</span>
											<span v-if="linkedCase.assigned_to">
												Assigned to: {{ linkedCase.assigned_to }}
											</span>
										</div>
									</div>
									<span
										class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': linkedCase.case_status === 'OPEN',
											'bg-yellow-100 text-yellow-800': linkedCase.case_status === 'IN_PROGRESS',
											'bg-green-100 text-green-800': linkedCase.case_status === 'CLOSED'
										}"
									>
										{{ linkedCase.case_status.replace("_", " ").toUpperCase() }}
									</span>
								</div>
							</div>
						</div>
					</div>

					<!-- Legacy Case IDs (for backward compatibility) -->
					<div v-else-if="selectedAlert.case_ids && selectedAlert.case_ids.length > 0">
						<label class="block text-sm font-medium text-gray-700">Linked Cases</label>
						<div class="mt-1 flex flex-wrap gap-2">
							<span
								v-for="caseId in selectedAlert.case_ids"
								:key="caseId"
								class="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800"
							>
								Case #{{ caseId }}
							</span>
						</div>
					</div>

					<!-- IoCs Section -->
					<div v-if="selectedAlert.iocs && selectedAlert.iocs.length > 0">
						<label class="mb-2 block text-sm font-medium text-gray-700">
							Indicators of Compromise (IoCs)
						</label>
						<div class="rounded-lg bg-gray-50 p-4">
							<div
								v-for="ioc in selectedAlert.iocs"
								:key="ioc.id"
								class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
							>
								<div class="grid grid-cols-1 gap-2 text-sm md:grid-cols-3">
									<div>
										<span class="font-medium">Value:</span>
										<code class="rounded bg-gray-100 px-1 text-xs">{{ ioc.ioc_value }}</code>
									</div>
									<div>
										<span class="font-medium">Type:</span>
										{{ ioc.ioc_type }}
									</div>
									<div>
										<span class="font-medium">Description:</span>
										{{ ioc.ioc_description }}
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Comments Section -->
					<div>
						<label class="mb-2 block text-sm font-medium text-gray-700">
							Comments
							<span
								v-if="selectedAlert.comments && selectedAlert.comments.length > 0"
								class="font-normal text-gray-500"
							>
								({{ selectedAlert.comments.length }})
							</span>
						</label>

						<!-- Existing Comments -->
						<div
							v-if="selectedAlert.comments && selectedAlert.comments.length > 0"
							class="mb-4 max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4"
						>
							<div
								v-for="comment in selectedAlert.comments"
								:key="comment.id"
								class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
							>
								<div class="mb-2 flex items-start justify-between">
									<span class="text-sm font-medium text-gray-900">{{ comment.user_name }}</span>
									<span class="text-xs text-gray-500">{{ formatDate(comment.created_at) }}</span>
								</div>
								<p class="text-sm whitespace-pre-wrap text-gray-700">{{ comment.comment }}</p>
							</div>
						</div>

						<!-- No Comments Message -->
						<div v-else class="mb-4 rounded-lg bg-gray-50 p-4 text-center">
							<p class="text-sm text-gray-500">No comments yet</p>
						</div>

						<!-- Add Comment Form -->
						<div class="rounded-lg border bg-white p-4">
							<label class="mb-2 block text-sm font-medium text-gray-700">Add Comment</label>
							<textarea
								v-model="newComment"
								placeholder="Enter your comment..."
								rows="3"
								class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
							></textarea>
							<div class="mt-3 flex justify-end">
								<button
									@click="addComment"
									:disabled="!newComment.trim() || isAddingComment"
									class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
								>
									<svg
										v-if="isAddingComment"
										class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
									>
										<circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
										></circle>
										<path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
										></path>
									</svg>
									{{ isAddingComment ? "Adding..." : "Add Comment" }}
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import AlertsAPI, { type Alert, type AlertsResponse } from "@/api/alerts"

const router = useRouter()
const portalSettingsStore = usePortalSettingsStore()

// Reactive data
const alerts = ref<Alert[]>([])
const stats = ref({
	total: 0,
	open: 0,
	in_progress: 0,
	closed: 0
})
const loading = ref(false)
const error = ref<string | null>(null)
const showLogo = ref(true)
const selectedAlert = ref<Alert | null>(null)
const updatingStatus = ref<number | null>(null)

// Comment management
const newComment = ref("")
const isAddingComment = ref(false)

// Pagination
const currentPage = ref(1)
const pageSize = ref(25)

// Filters
const filters = ref({
	status: "",
	source: "",
	asset: ""
})

// Computed properties
const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

const totalPages = computed(() => Math.ceil(stats.value.total / pageSize.value))

const availableSources = computed(() => {
	const sources = new Set(alerts.value.map(alert => alert.source))
	return Array.from(sources).sort()
})

const availableAssets = computed(() => {
	const assets = new Set(alerts.value.map(alert => alert.asset_name))
	return Array.from(assets).sort()
})

// Methods
const goBack = () => {
	router.push("/")
}

const loadAlerts = async () => {
	loading.value = true
	error.value = null

	try {
		let response: AlertsResponse

		if (filters.value.status) {
			response = await AlertsAPI.getAlertsByStatus(filters.value.status as any)
		} else if (filters.value.source) {
			response = await AlertsAPI.getAlertsBySource(filters.value.source)
		} else if (filters.value.asset) {
			response = await AlertsAPI.getAlertsByAsset(filters.value.asset)
		} else {
			response = await AlertsAPI.getAlerts(currentPage.value, pageSize.value)
		}

		alerts.value = response.alerts
		stats.value = {
			total: response.total,
			open: response.open,
			in_progress: response.in_progress,
			closed: response.closed
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load alerts"
		console.error("Error loading alerts:", err)
	} finally {
		loading.value = false
	}
}

const refreshAlerts = () => {
	loadAlerts()
}

const applyFilters = () => {
	currentPage.value = 1
	loadAlerts()
}

const updateAlertStatus = async (alertId: number, newStatus: string) => {
	updatingStatus.value = alertId

	try {
		await AlertsAPI.updateAlertStatus(alertId, newStatus as any)

		// Update the local alert status
		const alert = alerts.value.find(a => a.id === alertId)
		if (alert) {
			alert.status = newStatus as any
		}

		// Refresh stats
		await loadAlerts()
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to update alert status"
		console.error("Error updating alert status:", err)
	} finally {
		updatingStatus.value = null
	}
}

const viewAlert = (alert: Alert) => {
	selectedAlert.value = alert
}

const closeModal = () => {
	selectedAlert.value = null
	newComment.value = "" // Clear comment when closing modal
}

const addComment = async () => {
	if (!selectedAlert.value || !newComment.value.trim()) return

	isAddingComment.value = true
	try {
		// Make API call to add comment
		const response = await AlertsAPI.addComment({
			alert_id: selectedAlert.value.id,
			comment: newComment.value.trim(),
			user_name: "Customer User" // This should come from auth context later
		})

		// Add the new comment to the local array
		if (!selectedAlert.value.comments) {
			selectedAlert.value.comments = []
		}
		selectedAlert.value.comments.push(response.comment)

		// Clear the input
		newComment.value = ""
	} catch (err) {
		console.error("Failed to add comment:", err)
		// Handle error - maybe show a toast notification
		error.value = "Failed to add comment. Please try again."
	} finally {
		isAddingComment.value = false
	}
}

const formatDate = (dateString: string) => {
	return new Date(dateString).toLocaleString()
}

const previousPage = () => {
	if (currentPage.value > 1) {
		currentPage.value--
		loadAlerts()
	}
}

const nextPage = () => {
	if (currentPage.value < totalPages.value) {
		currentPage.value++
		loadAlerts()
	}
}

// Lifecycle
onMounted(() => {
	loadAlerts()
})
</script>
