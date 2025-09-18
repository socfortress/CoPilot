<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <button @click="goBack" class="mr-4 text-indigo-600 hover:text-indigo-500">
              ← Back
            </button>
            <h1 class="text-xl font-semibold text-gray-900">Security Cases</h1>
          </div>
          <div class="flex items-center space-x-4">
            <button
              @click="refreshCases"
              :disabled="loading"
              class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              <svg class="w-4 h-4 mr-2" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              Refresh
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Stats Cards -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"></path>
                    <path fill-rule="evenodd" d="M4 5a2 2 0 012-2v1a1 1 0 102 0V3a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 2a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">Total Cases</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ cases.length }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">Open</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ openCases }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">In Progress</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ inProgressCases }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
          <div class="p-5">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                  <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                  </svg>
                </div>
              </div>
              <div class="ml-5 w-0 flex-1">
                <dl>
                  <dt class="text-sm font-medium text-gray-500 truncate">Closed</dt>
                  <dd class="text-lg font-medium text-gray-900">{{ closedCases }}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="bg-white shadow rounded-lg mb-6">
        <div class="px-4 py-5 sm:p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label for="status-filter" class="block text-sm font-medium text-gray-700">Status</label>
              <select
                id="status-filter"
                v-model="filters.status"
                @change="applyFilters"
                class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div>
              <label for="assigned-to-filter" class="block text-sm font-medium text-gray-700">Assigned To</label>
              <select
                id="assigned-to-filter"
                v-model="filters.assignedTo"
                @change="applyFilters"
                class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">All Assignees</option>
                <option v-for="assignee in availableAssignees" :key="assignee" :value="assignee">{{ assignee }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Cases List -->
      <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <div v-if="loading" class="px-4 py-5 sm:p-6 text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p class="mt-2 text-sm text-gray-500">Loading cases...</p>
        </div>

        <div v-else-if="error" class="px-4 py-5 sm:p-6 text-center">
          <div class="text-red-500 mb-2">
            <svg class="w-8 h-8 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
          </div>
          <p class="text-sm text-red-600">{{ error }}</p>
          <button
            @click="loadCases"
            class="mt-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Try Again
          </button>
        </div>

        <ul v-else-if="filteredCases.length > 0" role="list" class="divide-y divide-gray-200">
          <li v-for="case_ in filteredCases" :key="case_.id" class="px-4 py-4 sm:px-6 hover:bg-gray-50">
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-red-100 text-red-800': case_.case_status === 'open',
                      'bg-yellow-100 text-yellow-800': case_.case_status === 'in_progress',
                      'bg-green-100 text-green-800': case_.case_status === 'closed'
                    }"
                  >
                    {{ case_.case_status.replace('_', ' ').toUpperCase() }}
                  </span>
                </div>
                <div class="ml-4">
                  <div class="text-sm font-medium text-gray-900">
                    {{ case_.case_name }}
                  </div>
                  <div class="text-sm text-gray-500">
                    Case #{{ case_.id }}
                    <span v-if="case_.assigned_to"> | Assigned to: {{ case_.assigned_to }}</span>
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
                  class="text-sm border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  :disabled="updatingStatus === case_.id"
                >
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="closed">Closed</option>
                </select>
                <button
                  @click="viewCase(case_)"
                  class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
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

        <div v-else class="px-4 py-5 sm:p-6 text-center">
          <svg class="w-12 h-12 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No cases found</h3>
          <p class="mt-1 text-sm text-gray-500">No security cases match your current filters.</p>
        </div>
      </div>
    </div>

    <!-- Case Details Modal -->
    <div v-if="selectedCase" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" @click="closeModal">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white" @click.stop>
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-medium text-gray-900">Case Details</h3>
          <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Case Name</label>
              <p class="mt-1 text-sm text-gray-900">{{ selectedCase.case_name }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Status</label>
              <span
                class="mt-1 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="{
                  'bg-red-100 text-red-800': selectedCase.case_status === 'open',
                  'bg-yellow-100 text-yellow-800': selectedCase.case_status === 'in_progress',
                  'bg-green-100 text-green-800': selectedCase.case_status === 'closed'
                }"
              >
                {{ selectedCase.case_status.replace('_', ' ').toUpperCase() }}
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
              <p class="mt-1 text-sm text-gray-900">{{ selectedCase.assigned_to || 'Unassigned' }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Created</label>
              <p class="mt-1 text-sm text-gray-900">{{ formatDate(selectedCase.case_creation_time) }}</p>
            </div>
          </div>

          <div v-if="selectedCase.case_description">
            <label class="block text-sm font-medium text-gray-700">Description</label>
            <p class="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{{ selectedCase.case_description }}</p>
          </div>

          <div v-if="selectedCase.alert_ids && selectedCase.alert_ids.length > 0">
            <label class="block text-sm font-medium text-gray-700">Linked Alerts</label>
            <div class="mt-1 flex flex-wrap gap-2">
              <span
                v-for="alertId in selectedCase.alert_ids"
                :key="alertId"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                Alert #{{ alertId }}
              </span>
            </div>
          </div>

          <div v-if="selectedCase.alerts && selectedCase.alerts.length > 0">
            <label class="block text-sm font-medium text-gray-700">Alert Details</label>
            <div class="mt-1 space-y-2">
              <div
                v-for="alert in selectedCase.alerts"
                :key="alert.id"
                class="p-3 bg-gray-50 rounded-md border"
              >
                <div class="flex justify-between items-start">
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ alert.alert_name }}</p>
                    <p class="text-xs text-gray-500">Asset: {{ alert.asset_name }}</p>
                  </div>
                  <span
                    class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                    :class="{
                      'bg-red-100 text-red-800': alert.status === 'open',
                      'bg-yellow-100 text-yellow-800': alert.status === 'in_progress',
                      'bg-green-100 text-green-800': alert.status === 'closed'
                    }"
                  >
                    {{ alert.status.replace('_', ' ').toUpperCase() }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Case Files Section -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="block text-sm font-medium text-gray-700">
                Case Files
                <span v-if="caseFiles.length > 0" class="text-gray-500 font-normal">
                  ({{ caseFiles.length }})
                </span>
              </label>
              <div class="flex items-center space-x-2">
                <button
                  @click="openUploadForm"
                  class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                  </svg>
                  Upload File
                </button>
                <button
                  v-if="!loadingFiles"
                  @click="loadCaseFiles(selectedCase.id)"
                  class="text-xs text-indigo-600 hover:text-indigo-500 focus:outline-none"
                >
                  <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                  </svg>
                  Refresh
                </button>
              </div>
            </div>

            <!-- Upload Form -->
            <div v-if="showUploadForm" class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-medium text-blue-900">Upload File to Case</h4>
                <button
                  @click="closeUploadForm"
                  class="text-blue-400 hover:text-blue-600"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>

              <div class="space-y-3">
                <div>
                  <input
                    ref="fileInput"
                    type="file"
                    @change="handleFileSelect"
                    class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 focus:outline-none"
                  />
                </div>

                <div v-if="selectedFile" class="text-sm text-gray-600">
                  Selected: {{ selectedFile.name }} ({{ CaseDataStoreAPI.formatFileSize(selectedFile.size) }})
                </div>

                <!-- Error message for upload -->
                <div v-if="error && showUploadForm" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-2">
                  {{ error }}
                </div>

                <div class="flex justify-end space-x-2">
                  <button
                    @click="closeUploadForm"
                    type="button"
                    class="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Cancel
                  </button>
                  <button
                    @click="uploadFile"
                    :disabled="!selectedFile || uploadingFile"
                    class="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="uploadingFile" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ uploadingFile ? 'Uploading...' : 'Upload File' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Loading Files -->
            <div v-if="loadingFiles" class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto"></div>
              <p class="mt-2 text-sm text-gray-500">Loading files...</p>
            </div>

            <!-- Files List -->
            <div v-else-if="caseFiles.length > 0" class="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
              <div v-for="file in caseFiles" :key="file.id" class="border-b border-gray-200 pb-3 mb-3 last:border-b-0 last:mb-0">
                <div class="flex justify-between items-start">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2">
                      <svg class="w-4 h-4 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                      <p class="text-sm font-medium text-gray-900 truncate">{{ file.file_name }}</p>
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
                    class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="downloadingFile === file.file_name" class="animate-spin -ml-1 mr-1 h-3 w-3 text-indigo-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <svg v-else class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    {{ downloadingFile === file.file_name ? 'Downloading...' : 'Download' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- No Files Message -->
            <div v-else class="bg-gray-50 rounded-lg p-4 text-center">
              <svg class="w-8 h-8 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <p class="mt-2 text-sm text-gray-500">No files available for this case</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import CasesAPI, { type Case, type CasesResponse } from '@/api/cases'
import CaseDataStoreAPI, { type CaseDataStoreFile } from '@/api/caseDataStore'

const router = useRouter()

// Reactive data
const cases = ref<Case[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedCase = ref<Case | null>(null)
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
  status: '',
  assignedTo: ''
})

// Computed properties
const openCases = computed(() => cases.value.filter(c => c.case_status === 'open').length)
const inProgressCases = computed(() => cases.value.filter(c => c.case_status === 'in_progress').length)
const closedCases = computed(() => cases.value.filter(c => c.case_status === 'closed').length)

const availableAssignees = computed(() => {
  const assignees = new Set(cases.value.map(c => c.assigned_to).filter((assignee): assignee is string => assignee !== null))
  return Array.from(assignees).sort()
})

const filteredCases = computed(() => {
  let filtered = cases.value

  if (filters.value.status) {
    filtered = filtered.filter(c => c.case_status === filters.value.status)
  }

  if (filters.value.assignedTo) {
    filtered = filtered.filter(c => c.assigned_to === filters.value.assignedTo)
  }

  return filtered.sort((a, b) => new Date(b.case_creation_time).getTime() - new Date(a.case_creation_time).getTime())
})

// Methods
const goBack = () => {
  router.push('/')
}

const loadCases = async () => {
  loading.value = true
  error.value = null

  try {
    let response: CasesResponse

    if (filters.value.status) {
      response = await CasesAPI.getCasesByStatus(filters.value.status as any)
    } else if (filters.value.assignedTo) {
      response = await CasesAPI.getCasesByAssignedTo(filters.value.assignedTo)
    } else {
      response = await CasesAPI.getCases()
    }

    cases.value = response.cases
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || 'Failed to load cases'
    console.error('Error loading cases:', err)
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
    error.value = err.response?.data?.detail || err.message || 'Failed to update case status'
    console.error('Error updating case status:', err)
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
    console.error('Error loading case files:', err)
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
    console.error('Error downloading file:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to download file'
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
    fileInput.value.value = ''
  }
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    // Check file size (e.g., limit to 50MB)
    const maxSize = 50 * 1024 * 1024 // 50MB in bytes
    if (file.size > maxSize) {
      error.value = 'File size too large. Maximum size is 50MB.'
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
    console.log('File uploaded successfully!')

  } catch (err: any) {
    console.error('Error uploading file:', err)

    // Extract more specific error messages
    let errorMessage = 'Failed to upload file'
    if (err.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        errorMessage = err.response.data.detail
      } else if (Array.isArray(err.response.data.detail)) {
        errorMessage = err.response.data.detail.map((e: any) => e.msg || e.message || e).join(', ')
      }
    } else if (err.message) {
      errorMessage = err.message
    }

    error.value = errorMessage
  } finally {
    uploadingFile.value = false
  }
}

const closeModal = () => {
  selectedCase.value = null
  caseFiles.value = []
  closeUploadForm()
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

// Lifecycle
onMounted(() => {
  loadCases()
})
</script>
