<template>
  <div class="empty-state-card">
    <div class="empty-state-icon">📊</div>
    <h2 class="empty-state-title">No data loaded yet</h2>
    <p class="empty-state-desc">Connect Anansi to your Jira project and load your team's issue data to see agile metrics.</p>
    <div class="empty-state-actions">
      <router-link to="/config" class="btn btn-primary">⚙ Set up Configuration</router-link>
      <button class="btn btn-secondary" @click="$emit('load')">⬇ Load Data</button>
    </div>
  </div>
</template>

<script setup>
defineEmits(['load'])
</script>
