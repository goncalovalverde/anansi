<template>
  <header class="app-header">
    <div class="container">
      <h1><span class="logo">⬡</span> Anansi</h1>
      <nav class="nav-links">
        <router-link to="/" :class="{ active: route.path === '/' }">Dashboard</router-link>
        <router-link to="/config" :class="{ active: route.path === '/config' }">Configuration</router-link>
      </nav>
      <button class="theme-toggle" @click="configStore.toggleTheme()" title="Toggle light/dark mode" aria-label="Toggle theme">
        {{ configStore.theme === 'light' ? '🌙' : '☀️' }}
      </button>
    </div>
  </header>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useConfigStore } from '@/stores/config.js'
const route = useRoute()
const configStore = useConfigStore()
</script>
