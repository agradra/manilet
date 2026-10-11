<script>
    import { onMount } from 'svelte';
    import { getCurrentWindow } from '@tauri-apps/api/window';
    import { settingsStore, initSettings } from '../lib/settings.js';

    export let allowPin = false; // 항상 위 고정 버튼 표시 여부
    let isAlwaysOnTop = false;

    const appWindow = getCurrentWindow();

    onMount(() => {
        initSettings();
    });

    $: isMac = $settingsStore.effective_window_control_style === 'mac';

    function minimize() {
        appWindow.minimize();
    }

    async function toggleMaximize() {
        const maximized = await appWindow.isMaximized();
        if (maximized) {
            appWindow.unmaximize();
        } else {
            appWindow.maximize();
        }
    }

    function closeWindow() {
        appWindow.close();
    }

    async function toggleAlwaysOnTop() {
        isAlwaysOnTop = !isAlwaysOnTop;
        await appWindow.setAlwaysOnTop(isAlwaysOnTop);
    }
</script>

{#if isMac}
    <!-- macOS 스타일 트래픽 라이트 (Close, Minimize, Maximize) -->
    <div class="mac-controls">
        <button class="mac-btn close" title="닫기" on:click={closeWindow}>
            <span class="symbol">✕</span>
        </button>
        <button class="mac-btn minimize" title="최소화" on:click={minimize}>
            <span class="symbol">−</span>
        </button>
        <button class="mac-btn maximize" title="최대화" on:click={toggleMaximize}>
            <span class="symbol">+</span>
        </button>
        {#if allowPin}
            <button
                class="mac-pin-btn"
                class:active={isAlwaysOnTop}
                title={isAlwaysOnTop ? "항상 위 해제" : "항상 위 고정"}
                on:click={toggleAlwaysOnTop}
            >
                📌
            </button>
        {/if}
    </div>
{:else}
    <!-- Windows 스타일 컨트롤 -->
    <div class="win-controls">
        {#if allowPin}
            <button
                class="win-btn pin"
                class:active={isAlwaysOnTop}
                title={isAlwaysOnTop ? "항상 위 해제" : "항상 위 고정"}
                on:click={toggleAlwaysOnTop}
            >
                📌
            </button>
        {/if}
        <button class="win-btn minimize" title="최소화" on:click={minimize}>−</button>
        <button class="win-btn maximize" title="최대화" on:click={toggleMaximize}>□</button>
        <button class="win-btn close" title="닫기" on:click={closeWindow}>✕</button>
    </div>
{/if}

<style>
    /* ================= macOS 스타일 ================= */
    .mac-controls {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 10px;
        height: 100%;
        -webkit-app-region: no-drag;
    }

    .mac-btn {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: none;
        padding: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        position: relative;
        transition: filter 0.15s, transform 0.1s;
    }

    .mac-btn:active {
        transform: scale(0.92);
    }

    .mac-btn.close {
        background-color: #ff5f56;
        box-shadow: inset 0 0 0 1px #e0443e;
    }

    .mac-btn.minimize {
        background-color: #ffbd2e;
        box-shadow: inset 0 0 0 1px #dea123;
    }

    .mac-btn.maximize {
        background-color: #27c93f;
        box-shadow: inset 0 0 0 1px #1aab29;
    }

    .mac-btn .symbol {
        font-size: 8px;
        font-weight: 700;
        color: rgba(0, 0, 0, 0.6);
        opacity: 0;
        transition: opacity 0.12s;
        pointer-events: none;
        line-height: 1;
    }

    /* 그룹에 마우스 올리면 심볼 노출 */
    .mac-controls:hover .symbol {
        opacity: 1;
    }

    .mac-pin-btn {
        background: transparent;
        border: none;
        font-size: 11px;
        opacity: 0.5;
        cursor: pointer;
        padding: 2px 4px;
        border-radius: 4px;
        margin-left: 4px;
        transition: opacity 0.15s, background-color 0.15s;
    }

    .mac-pin-btn:hover {
        opacity: 1;
        background-color: rgba(255, 255, 255, 0.1);
    }

    .mac-pin-btn.active {
        opacity: 1;
        background-color: rgba(192, 132, 252, 0.25);
    }

    /* ================= Windows 스타일 ================= */
    .win-controls {
        display: flex;
        align-items: center;
        height: 100%;
        -webkit-app-region: no-drag;
    }

    .win-btn {
        background: transparent;
        border: none;
        color: #cccccc;
        width: 44px;
        height: 32px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        font-size: 12px;
        transition: background-color 0.15s, color 0.15s;
    }

    .win-btn:hover {
        background-color: rgba(255, 255, 255, 0.1);
        color: #ffffff;
    }

    .win-btn.pin {
        font-size: 11px;
        opacity: 0.6;
    }

    .win-btn.pin:hover {
        opacity: 1;
    }

    .win-btn.pin.active {
        opacity: 1;
        background-color: rgba(192, 132, 252, 0.2);
        color: var(--accent, #c084fc);
    }

    .win-btn.close:hover {
        background-color: #e81123;
        color: white;
    }
</style>
