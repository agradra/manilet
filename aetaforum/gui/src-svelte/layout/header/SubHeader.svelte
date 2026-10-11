<script>
    import { onMount } from "svelte";
    import WindowControls from "../../ui/WindowControls.svelte";
    import { settingsStore, initSettings } from "../../lib/settings.js";

    export let title = "Window";
    export let allowPin = true;

    onMount(() => {
        initSettings();
    });

    $: isMac = $settingsStore.effective_window_control_style === "mac";
</script>

<div class="titlebar sub-header" data-tauri-drag-region>
    {#if isMac}
        <div class="mac-controls-slot">
            <WindowControls {allowPin} />
        </div>
    {/if}

    <div class="drag-area" data-tauri-drag-region>
        <span class="title">{title}</span>
    </div>

    <!-- 서브 창 전용 액션 (도킹 버튼, 추가 컨트롤 등) -->
    <div class="header-actions">
        <slot />
    </div>

    {#if !isMac}
        <WindowControls {allowPin} />
    {/if}
</div>

<style>
    .titlebar {
        display: flex;
        align-items: center;
        height: 32px;
        background-color: var(--bg);
        user-select: none;
        width: 100%;
        border-bottom: 1px solid #333;
        box-sizing: border-box;
    }

    .mac-controls-slot {
        display: flex;
        align-items: center;
        height: 100%;
    }

    .drag-area {
        flex: 1;
        display: flex;
        align-items: center;
        padding-left: 12px;
        height: 100%;
        cursor: default;
    }

    .title {
        color: #cccccc;
        font-size: 13px;
        font-weight: 600;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        pointer-events: none;
    }

    .header-actions {
        display: flex;
        align-items: center;
        margin-right: 10px;
        -webkit-app-region: no-drag;
    }
</style>
