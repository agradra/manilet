<script>
    import { invoke } from "@tauri-apps/api/core";

    function minimize() {
        invoke("minimize_window");
    }
    function toggleMaximize() {
        invoke("toggle_maximize_window");
    }
    function closeWindow() {
        invoke("close_window");
    }
</script>

<div class="titlebar" data-tauri-drag-region>
    <div class="drag-area" data-tauri-drag-region>
        <span class="title">Aetaforum</span>
    </div>
    <div class="window-controls">
        <button class="control-btn minimize" on:click={minimize}>−</button>
        <button class="control-btn maximize" on:click={toggleMaximize}>□</button
        >
        <button class="control-btn close" on:click={closeWindow}>✕</button>
    </div>
</div>

<style>
    .titlebar {
        display: flex;
        height: 32px;
        background-color: var(--bg);
        user-select: none;
        width: 100%;
        border-bottom: 1px solid #333;
        margin: 20px;
        border-radius: 20px;
    }

    .drag-area {
        flex: 1;
        display: flex;
        align-items: center;
        padding-left: 12px;
        cursor: default;
    }

    .title {
        color: #cccccc;
        font-size: 13px;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        pointer-events: none;
    }

    .window-controls {
        display: flex;
        -webkit-app-region: no-drag; /* 드래그 방지 */
    }

    .control-btn {
        background: transparent;
        border: none;
        color: #cccccc;
        width: 46px;
        height: 32px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        font-size: 12px;
    }

    .control-btn:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }

    .control-btn.close:hover {
        background-color: #e81123;
        color: white;
    }
</style>
