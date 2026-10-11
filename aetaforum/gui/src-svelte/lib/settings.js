import { writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

export const settingsStore = writable({
    window_control_style: 'system',
    effective_window_control_style: 'windows',
    os: 'windows'
});

let isInitialized = false;

export async function initSettings() {
    if (isInitialized) return;
    isInitialized = true;

    try {
        const response = await invoke('load_settings');
        settingsStore.set({
            window_control_style: response.settings.window_control_style,
            effective_window_control_style: response.effective_window_control_style,
            os: response.os
        });
    } catch (e) {
        console.warn('Failed to load settings from Rust:', e);
    }

    try {
        await listen('settings-updated', (event) => {
            const payload = event.payload;
            settingsStore.set({
                window_control_style: payload.settings.window_control_style,
                effective_window_control_style: payload.effective_window_control_style,
                os: payload.os
            });
        });
    } catch (e) {
        console.warn('Failed to register settings-updated listener:', e);
    }
}

export async function saveSettings(newSettings) {
    try {
        const response = await invoke('save_settings', { settings: newSettings });
        settingsStore.set({
            window_control_style: response.settings.window_control_style,
            effective_window_control_style: response.effective_window_control_style,
            os: response.os
        });
        return response;
    } catch (e) {
        console.error('Failed to save settings:', e);
        throw e;
    }
}
