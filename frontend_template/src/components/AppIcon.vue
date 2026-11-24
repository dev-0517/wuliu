<script setup>
defineProps({ name: String, size: { type: Number, default: 20 } })
const paths = {
  book: 'M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Z M12 5v15',
  calendar: 'M4 5h16v16H4z M8 2v6 M16 2v6 M4 10h16 M8 14h2 M14 14h2 M8 18h2',
  sun: 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5 19 19 M5 19l1.5-1.5 M17.5 6.5 19 5',
  case: 'M3 7h18v13H3z M8 7V4h8v3 M3 12h18 M10 12v3h4v-3',
  chat: 'M21 11a8 8 0 0 1-8 8H6l-4 3V11a9 9 0 0 1 19 0Z M7 10h10 M7 14h6',
  history: 'M3 11a9 9 0 1 1 2 7 M3 4v7h7 M12 7v5l3 2',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2',
  plus: 'M12 5v14 M5 12h14', search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  arrow: 'M5 12h14 M13 6l6 6-6 6', back: 'M19 12H5 M11 6l-6 6 6 6',
  spark: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z',
  file: 'M5 3h9l5 5v13H5z M14 3v6h5 M8 13h8 M8 17h6',
  check: 'm5 12 4 4L19 6', trash: 'M3 6h18 M9 6V3h6v3 M6 6l1 15h10l1-15 M10 10v7 M14 10v7',
  logout: 'M10 4H4v16h6 M9 12h12 M16 7l5 5-5 5',
  shield: 'm12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Z m-5 10 3 3 7-7',
  send: 'm22 2-7 20-4-9-9-4L22 2Z M11 13 22 2',
  edit: 'm16 3 5 5-12 12-6 1 1-6L16 3Z M13 6l5 5',
}
</script>
<template><svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.file" /></svg></template>
