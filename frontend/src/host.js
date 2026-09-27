import { ref } from "vue";

// The navbar greets the host by name, and the profile page can rename them.
export const firstName = ref(window.first_name || window.session_user);
