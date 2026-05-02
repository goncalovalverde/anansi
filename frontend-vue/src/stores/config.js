import { defineStore } from 'pinia'

export const useConfigStore = defineStore('config', {
  state: () => ({
    theme: localStorage.getItem('anansi_theme') || 'light',
  }),
  actions: {
    setTheme(t) {
      this.theme = t
      localStorage.setItem('anansi_theme', t)
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    },
  },
})
