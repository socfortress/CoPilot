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
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
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
							@click="refreshCases"
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
							<div class="shrink-0">
								<div class="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500">
									<svg class="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
										<path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"></path>
										<path
											fill-rule="evenodd"
											d="M4 5a2 2 0 012-2v1a1 1 0 102 0V3a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 2a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
											clip-rule="evenodd"
										></path>
									</svg>
								</div>
							</div>
							<div class="ml-5 w-0 flex-1">
								<dl>
									<dt class="truncate text-sm font-medium text-gray-500">Total Cases</dt>
									<dd class="text-lg font-medium text-gray-900">{{ cases.length }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>

				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="shrink-0">
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
									<dd class="text-lg font-medium text-gray-900">{{ openCases }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>

				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="shrink-0">
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
									<dd class="text-lg font-medium text-gray-900">{{ inProgressCases }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>

				<div class="overflow-hidden rounded-lg bg-white shadow">
					<div class="p-5">
						<div class="flex items-center">
							<div class="shrink-0">
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
									<dd class="text-lg font-medium text-gray-900">{{ closedCases }}</dd>
								</dl>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Filters -->
			<div class="mb-6 rounded-lg bg-white shadow">
				<div class="px-4 py-5 sm:p-6">
					<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
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
							<label for="assigned-to-filter" class="block text-sm font-medium text-gray-700">
								Assigned To
							</label>
							<select
								id="assigned-to-filter"
								v-model="filters.assignedTo"
								@change="applyFilters"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="">All Assignees</option>
								<option v-for="assignee in availableAssignees" :key="assignee" :value="assignee">
									{{ assignee }}
								</option>
							</select>
						</div>
					</div>
				</div>
			</div>

			<!-- Cases List -->
			<div class="overflow-hidden bg-white shadow sm:rounded-md">
				<div v-if="loading" class="px-4 py-5 text-center sm:p-6">
					<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
					<p class="mt-2 text-sm text-gray-500">Loading cases...</p>
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
						@click="loadCases"
						class="mt-2 inline-flex items-center rounded-md border border-transparent bg-indigo-100 px-3 py-2 text-sm leading-4 font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
					>
						Try Again
					</button>
				</div>

				<ul v-else-if="filteredCases.length > 0" role="list" class="divide-y divide-gray-200">
					<li v-for="case_ in filteredCases" :key="case_.id" class="px-4 py-4 hover:bg-gray-50 sm:px-6">
						<div class="flex items-center justify-between">
							<div class="flex items-center">
								<div class="shrink-0">
									<span
										class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': case_.case_status?.toLowerCase() === 'open',
											'bg-yellow-100 text-yellow-800':
												case_.case_status?.toLowerCase() === 'in_progress',
											'bg-green-100 text-green-800': case_.case_status?.toLowerCase() === 'closed'
										}"
									>
										{{ case_.case_status?.replace("_", " ").toUpperCase() }}
									</span>
								</div>
								<div class="ml-4">
									<div class="text-sm font-medium text-gray-900">
										{{ case_.case_name }}
									</div>
									<div class="text-sm text-gray-500">
										Case #{{ case_.id }}
										<span v-if="case_.assigned_to">| Assigned to: {{ case_.assigned_to }}</span>
									</div>
									<div class="text-xs text-gray-400">
										Created: {{ formatDate(case_.case_creation_time) }}
									</div>
								</div>
							</div>
							<div class="flex items-center space-x-2">
								<select
									:value="case_.case_status"
									@change="updateCaseStatus(case_.id, ($event.target as HTMLSelectElement).value)"
									class="rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
									:disabled="updatingStatus === case_.id"
								>
									<option value="open">Open</option>
									<option value="in_progress">In Progress</option>
									<option value="closed">Closed</option>
								</select>
								<button
									@click="viewCase(case_)"
									class="inline-flex items-center rounded border border-transparent bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									View Details
								</button>
							</div>
						</div>
						<div v-if="case_.case_description" class="mt-2 text-sm text-gray-600">
							{{ case_.case_description }}
						</div>
						<div v-if="case_.alert_ids && case_.alert_ids.length > 0" class="mt-2">
							<span class="text-xs text-gray-500">Linked Alerts: {{ case_.alert_ids.length }}</span>
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
					<h3 class="mt-2 text-sm font-medium text-gray-900">No cases found</h3>
					<p class="mt-1 text-sm text-gray-500">No security cases match your current filters.</p>
				</div>
			</div>
		</div>

		<!-- Case Details Modal -->
		<div
			v-if="selectedCase"
			class="bg-opacity-50 fixed inset-0 z-50 h-full w-full overflow-y-auto bg-gray-600"
			@click="closeModal"
		>
			<div
				class="relative top-20 mx-auto w-11/12 rounded-md border bg-white p-5 shadow-lg md:w-3/4 lg:w-1/2"
				@click.stop
			>
				<div class="mb-4 flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900">Case Details</h3>
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

				<div class="space-y-4">
					<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
						<div>
							<label class="block text-sm font-medium text-gray-700">Case Name</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedCase.case_name }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Status</label>
							<span
								class="mt-1 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
								:class="{
									'bg-red-100 text-red-800': selectedCase.case_status?.toLowerCase() === 'open',
									'bg-yellow-100 text-yellow-800':
										selectedCase.case_status?.toLowerCase() === 'in_progress',
									'bg-green-100 text-green-800': selectedCase.case_status?.toLowerCase() === 'closed'
								}"
							>
								{{ selectedCase.case_status?.replace("_", " ").toUpperCase() }}
							</span>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Case ID</label>
							<p class="mt-1 text-sm text-gray-900">#{{ selectedCase.id }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Customer</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedCase.customer_code }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Assigned To</label>
							<p class="mt-1 text-sm text-gray-900">{{ selectedCase.assigned_to || "Unassigned" }}</p>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700">Created</label>
							<p class="mt-1 text-sm text-gray-900">{{ formatDate(selectedCase.case_creation_time) }}</p>
						</div>
					</div>

					<div v-if="selectedCase.case_description">
						<label class="block text-sm font-medium text-gray-700">Description</label>
						<p class="mt-1 text-sm whitespace-pre-wrap text-gray-900">
							{{ selectedCase.case_description }}
						</p>
					</div>

					<div v-if="selectedCase.alert_ids && selectedCase.alert_ids.length > 0">
						<label class="block text-sm font-medium text-gray-700">Linked Alerts</label>
						<div class="mt-1 flex flex-wrap gap-2">
							<span
								v-for="alertId in selectedCase.alert_ids"
								:key="alertId"
								class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
							>
								Alert #{{ alertId }}
							</span>
						</div>
					</div>

					<div v-if="selectedCase.alerts && selectedCase.alerts.length > 0">
						<div class="mb-2 flex items-center justify-between">
							<label class="block text-sm font-medium text-gray-700">Alert Details</label>
							<span class="text-xs text-gray-500">Click alerts to view details</span>
						</div>
						<div class="mt-1 space-y-2">
							<div
								v-for="alert in selectedCase.alerts"
								:key="alert.id"
								class="cursor-pointer rounded-md border bg-gray-50 p-3 transition-colors hover:bg-gray-100"
								@click="viewAlert(alert.id)"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center space-x-2">
											<p class="text-sm font-medium text-gray-900">{{ alert.alert_name }}</p>
											<svg
												class="h-4 w-4 text-gray-400"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-2M7 7l10 10M17 7v4h-4"
												></path>
											</svg>
										</div>
										<p class="text-xs text-gray-500">Asset: {{ alert.asset_name }}</p>
									</div>
									<span
										class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium"
										:class="{
											'bg-red-100 text-red-800': alert.status === 'OPEN',
											'bg-yellow-100 text-yellow-800': alert.status === 'IN_PROGRESS',
											'bg-green-100 text-green-800': alert.status === 'CLOSED'
										}"
									>
										{{ alert.status.replace("_", " ").toUpperCase() }}
									</span>
								</div>
							</div>
						</div>
					</div>

					<!-- Case Files Section -->
					<div>
						<div class="mb-2 flex items-center justify-between">
							<label class="block text-sm font-medium text-gray-700">
								Case Files
								<span v-if="caseFiles.length > 0" class="font-normal text-gray-500">
									({{ caseFiles.length }})
								</span>
							</label>
							<div class="flex items-center space-x-2">
								<button
									@click="openUploadForm"
									class="inline-flex items-center rounded border border-transparent bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
								>
									<svg class="mr-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
										></path>
									</svg>
									Upload File
								</button>
								<button
									v-if="!loadingFiles"
									@click="loadCaseFiles(selectedCase.id)"
									class="text-xs text-indigo-600 hover:text-indigo-500 focus:outline-none"
								>
									<svg
										class="mr-1 inline h-4 w-4"
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

						<!-- Upload Form -->
						<div v-if="showUploadForm" class="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
							<div class="mb-3 flex items-center justify-between">
								<h4 class="text-sm font-medium text-blue-900">Upload File to Case</h4>
								<button @click="closeUploadForm" class="text-blue-400 hover:text-blue-600">
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18L18 6M6 6l12 12"
										></path>
									</svg>
								</button>
							</div>

							<div class="space-y-3">
								<div>
									<input
										ref="fileInput"
										type="file"
										@change="handleFileSelect"
										class="block w-full text-sm text-gray-500 file:mr-4 file:rounded-full file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-indigo-700 hover:file:bg-indigo-100 focus:outline-none"
									/>
								</div>

								<div v-if="selectedFile" class="text-sm text-gray-600">
									Selected: {{ selectedFile.name }} ({{
										CaseDataStoreAPI.formatFileSize(selectedFile.size)
									}})
								</div>

								<!-- Error message for upload -->
								<div
									v-if="error && showUploadForm"
									class="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-600"
								>
									{{ error }}
								</div>

								<div class="flex justify-end space-x-2">
									<button
										@click="closeUploadForm"
										type="button"
										class="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
									>
										Cancel
									</button>
									<button
										@click="uploadFile"
										:disabled="!selectedFile || uploadingFile"
										class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
									>
										<svg
											v-if="uploadingFile"
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
										{{ uploadingFile ? "Uploading..." : "Upload File" }}
									</button>
								</div>
							</div>
						</div>

						<!-- Loading Files -->
						<div v-if="loadingFiles" class="rounded-lg bg-gray-50 p-4 text-center">
							<div class="mx-auto h-6 w-6 animate-spin rounded-full border-b-2 border-indigo-600"></div>
							<p class="mt-2 text-sm text-gray-500">Loading files...</p>
						</div>

						<!-- Files List -->
						<div
							v-else-if="caseFiles.length > 0"
							class="max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4"
						>
							<div
								v-for="file in caseFiles"
								:key="file.id"
								class="mb-3 border-b border-gray-200 pb-3 last:mb-0 last:border-b-0"
							>
								<div class="flex items-start justify-between">
									<div class="min-w-0 flex-1">
										<div class="flex items-center space-x-2">
											<svg
												class="h-4 w-4 shrink-0 text-gray-500"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
												></path>
											</svg>
											<p class="truncate text-sm font-medium text-gray-900">
												{{ file.file_name }}
											</p>
										</div>
										<div class="mt-1 flex items-center space-x-4 text-xs text-gray-500">
											<span>{{ CaseDataStoreAPI.formatFileSize(file.file_size) }}</span>
											<span v-if="file.content_type">{{ file.content_type }}</span>
											<span>{{ formatDate(file.upload_time) }}</span>
										</div>
									</div>
									<button
										@click="downloadFile(selectedCase.id, file.file_name)"
										:disabled="downloadingFile === file.file_name"
										class="ml-3 inline-flex items-center rounded border border-transparent bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-200 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
									>
										<svg
											v-if="downloadingFile === file.file_name"
											class="mr-1 -ml-1 h-3 w-3 animate-spin text-indigo-700"
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
										<svg
											v-else
											class="mr-1 h-3 w-3"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											></path>
										</svg>
										{{ downloadingFile === file.file_name ? "Downloading..." : "Download" }}
									</button>
								</div>
							</div>
						</div>

						<!-- No Files Message -->
						<div v-else class="rounded-lg bg-gray-50 p-4 text-center">
							<svg
								class="mx-auto h-8 w-8 text-gray-400"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
								></path>
							</svg>
							<p class="mt-2 text-sm text-gray-500">No files available for this case</p>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Alert Details Modal -->
		<div
			v-if="selectedAlert"
			class="bg-opacity-50 fixed inset-0 z-50 h-full w-full overflow-y-auto bg-gray-600"
			@click="closeAlertModal"
		>
			<div
				class="relative top-10 mx-auto max-h-screen w-11/12 overflow-y-auto rounded-md border bg-white p-5 shadow-lg md:w-4/5 lg:w-3/4"
				@click.stop
			>
				<div class="mb-4 flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900">Alert Details</h3>
					<button @click="closeAlertModal" class="text-gray-400 hover:text-gray-600">
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
								{{ selectedAlert.status.replace("_", " ") }}
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
										{{ linkedCase.case_status.replace("_", " ") }}
									</span>
								</div>
							</div>
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
					<div v-if="selectedAlert.comments && selectedAlert.comments.length > 0">
						<label class="mb-2 block text-sm font-medium text-gray-700">
							Comments ({{ selectedAlert.comments.length }})
						</label>
						<div class="max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4">
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
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import CasesAPI, { type Case, type CasesResponse } from "@/api/cases"
import CaseDataStoreAPI, { type CaseDataStoreFile } from "@/api/caseDataStore"
import AlertsAPI, { type Alert } from "@/api/alerts"

const portalSettingsStore = usePortalSettingsStore()

// Reactive data
const cases = ref<Case[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const showLogo = ref(true)
const selectedCase = ref<Case | null>(null)
const selectedAlert = ref<Alert | null>(null)
const updatingStatus = ref<number | null>(null)

// Case files data
const caseFiles = ref<CaseDataStoreFile[]>([])
const loadingFiles = ref(false)
const downloadingFile = ref<string | null>(null)

// File upload data
const uploadingFile = ref(false)
const selectedFile = ref<File | null>(null)
const showUploadForm = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// Filters
const filters = ref({
	status: "",
	assignedTo: ""
})

// Computed properties
const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

const openCases = computed(() => cases.value.filter(c => c.case_status?.toLowerCase() === "open").length)
const inProgressCases = computed(() => cases.value.filter(c => c.case_status?.toLowerCase() === "in_progress").length)
const closedCases = computed(() => cases.value.filter(c => c.case_status?.toLowerCase() === "closed").length)

const availableAssignees = computed(() => {
	const assignees = new Set(
		cases.value.map(c => c.assigned_to).filter((assignee): assignee is string => assignee !== null)
	)
	return Array.from(assignees).sort()
})

const filteredCases = computed(() => {
	let filtered = cases.value

	if (filters.value.status) {
		filtered = filtered.filter(c => c.case_status?.toLowerCase() === filters.value.status.toLowerCase())
	}

	if (filters.value.assignedTo) {
		filtered = filtered.filter(c => c.assigned_to === filters.value.assignedTo)
	}

	return filtered.sort((a, b) => new Date(b.case_creation_time).getTime() - new Date(a.case_creation_time).getTime())
})

const loadCases = async () => {
	loading.value = true
	error.value = null

	try {
		let response: CasesResponse

		if (filters.value.status) {
			// Convert lowercase filter to uppercase for backend API
			const backendStatus = filters.value.status.toUpperCase() as any
			response = await CasesAPI.getCasesByStatus(backendStatus)
		} else if (filters.value.assignedTo) {
			response = await CasesAPI.getCasesByAssignedTo(filters.value.assignedTo)
		} else {
			response = await CasesAPI.getCases()
		}

		cases.value = response.cases
		console.log("Loaded cases:", response.cases)
		console.log(
			"Case statuses:",
			response.cases.map(c => c.case_status)
		)
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load cases"
		console.error("Error loading cases:", err)
	} finally {
		loading.value = false
	}
}

const refreshCases = () => {
	loadCases()
}

const applyFilters = () => {
	// Since we use computed filteredCases, we don't need to reload from API for local filtering
	// But if we want to filter on the server side, we can call loadCases()
	loadCases()
}

const updateCaseStatus = async (caseId: number, newStatus: string) => {
	updatingStatus.value = caseId

	try {
		await CasesAPI.updateCaseStatus(caseId, newStatus as any)

		// Update the local case status
		const case_ = cases.value.find(c => c.id === caseId)
		if (case_) {
			case_.case_status = newStatus as any
		}
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to update case status"
		console.error("Error updating case status:", err)
	} finally {
		updatingStatus.value = null
	}
}

const viewCase = (case_: Case) => {
	selectedCase.value = case_
	loadCaseFiles(case_.id)
}

const loadCaseFiles = async (caseId: number) => {
	loadingFiles.value = true
	try {
		const response = await CaseDataStoreAPI.getCaseFiles(caseId)
		caseFiles.value = response.case_data_store
	} catch (err: any) {
		console.error("Error loading case files:", err)
		caseFiles.value = []
	} finally {
		loadingFiles.value = false
	}
}

const downloadFile = async (caseId: number, fileName: string) => {
	downloadingFile.value = fileName
	try {
		const blob = await CaseDataStoreAPI.downloadCaseFile(caseId, fileName)
		CaseDataStoreAPI.downloadFileBlob(blob, fileName)
	} catch (err: any) {
		console.error("Error downloading file:", err)
		error.value = err.response?.data?.detail || err.message || "Failed to download file"
	} finally {
		downloadingFile.value = null
	}
}

const openUploadForm = () => {
	showUploadForm.value = true
	selectedFile.value = null
	error.value = null
}

const closeUploadForm = () => {
	showUploadForm.value = false
	selectedFile.value = null
	if (fileInput.value) {
		fileInput.value.value = ""
	}
}

const handleFileSelect = (event: Event) => {
	const target = event.target as HTMLInputElement
	if (target.files && target.files.length > 0) {
		const file = target.files[0]
		// Check file size (e.g., limit to 50MB)
		const maxSize = 50 * 1024 * 1024 // 50MB in bytes
		if (file.size > maxSize) {
			error.value = "File size too large. Maximum size is 50MB."
			selectedFile.value = null
			return
		}
		selectedFile.value = file
		error.value = null // Clear any previous errors
	}
}

const uploadFile = async () => {
	if (!selectedFile.value || !selectedCase.value) return

	uploadingFile.value = true
	error.value = null

	try {
		await CaseDataStoreAPI.uploadCaseFile(selectedCase.value.id, selectedFile.value)

		// Refresh the files list
		await loadCaseFiles(selectedCase.value.id)

		// Close the upload form
		closeUploadForm()

		// You could add a success message here if you have a toast/notification system
		console.log("File uploaded successfully!")
	} catch (err: any) {
		console.error("Error uploading file:", err)

		// Extract more specific error messages
		let errorMessage = "Failed to upload file"
		if (err.response?.data?.detail) {
			if (typeof err.response.data.detail === "string") {
				errorMessage = err.response.data.detail
			} else if (Array.isArray(err.response.data.detail)) {
				errorMessage = err.response.data.detail.map((e: any) => e.msg || e.message || e).join(", ")
			}
		} else if (err.message) {
			errorMessage = err.message
		}

		error.value = errorMessage
	} finally {
		uploadingFile.value = false
	}
}

const viewAlert = async (alertId: number) => {
	try {
		const response = await AlertsAPI.getAlert(alertId)
		selectedAlert.value = response.alerts[0] // AlertResponse contains alerts array
	} catch (err: any) {
		console.error("Error loading alert details:", err)
		error.value = err.response?.data?.detail || err.message || "Failed to load alert details"
	}
}

const closeAlertModal = () => {
	selectedAlert.value = null
}

const closeModal = () => {
	selectedCase.value = null
	caseFiles.value = []
	closeUploadForm()
	closeAlertModal()
}

const formatDate = (dateString: string) => {
	return new Date(dateString).toLocaleString()
}

// Lifecycle
onMounted(() => {
	loadCases()
})
</script>
