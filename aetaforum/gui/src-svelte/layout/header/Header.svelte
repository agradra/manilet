<script>
    import { invoke } from "@tauri-apps/api/core";
    import { WebviewWindow } from "@tauri-apps/api/webviewWindow";
    import MacCB from "./parts/window_control/Mac.svelte";
    import WinCB from "./parts/window_control/Windows.svelte";

    import WindowLockButton from "./parts/WindowLockButton.svelte";

    import { onMount } from "svelte";
    import { listen } from "@tauri-apps/api/event";
    import Spacer from "../../ui/Spacer.svelte";

    let window_control_mode = $state("win");
    let { children } = $props();

    onMount(() => {
        invoke("get_window_control_mode")
            .then((mode) => {
                window_control_mode = mode;
            })
            .catch((err) => console.error(err));

        const unlistenPromise = listen("window-control-mode", (event) => {
            window_control_mode = event.payload;
            console.log(
                "상단바 창 제어 버튼 디자인 변경:",
                window_control_mode,
            );
        });

        return () => {
            unlistenPromise.then((unlisten) => unlisten());
        };
    });
</script>

<header class="titlebar main-header" data-tauri-drag-region>
    {#if window_control_mode === "mac"}
        <MacCB />
        <Spacer />
        <WindowLockButton />
    {:else if window_control_mode === "win"}
        <WindowLockButton />
        <Spacer />
        <WinCB />
    {/if}
</header>

<style>
    .titlebar {
        display: flex;
        align-items: center;
        height: 30px;
        background-color: transparent;
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

    .icon-btn {
        background: transparent;
        border: none;
        color: var(--text, #9ca3af);
        font-size: 1.1rem;
        width: 28px;
        height: 28px;
        border-radius: 4px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        transition:
            background 0.2s,
            color 0.2s;
    }

    .icon-btn:hover {
        background: rgba(255, 255, 255, 0.1);
        color: var(--text-h, #f3f4f6);
    }
</style>
