<template>
  <div v-if="insights && insights.length" class="insight-bar">
    <span
      v-for="(pill, i) in insights"
      :key="i"
      class="insight-pill"
      :class="pill.type"
    >
      <span class="insight-pill-dot"></span>
      {{ pill.message }}
    </span>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { useDataStore } from '@/stores/data.js'
const store = useDataStore()
const insights = computed(() => store.insights)
</script>
