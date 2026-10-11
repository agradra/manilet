<script>
    import { getCurrentWindow } from "@tauri-apps/api/window";
    import { onMount } from "svelte";

    const NOW_WINDOW = getCurrentWindow();

    let isPinned = $state(false);

    onMount(() => {
        // 창 초기 항상 위(Always On Top) 상태 감지
        (async () => {
            try {
                if (typeof NOW_WINDOW.isAlwaysOnTop === "function") {
                    isPinned = await NOW_WINDOW.isAlwaysOnTop();
                }
            } catch (err) {
                // 브라우저 미리보기 등 예외 환경에서는 기본값(false) 유지
            }
        })();
    });

    // 창 고정 및 최상단 유지 토글 함수
    async function togglePin() {
        try {
            const nextPinned = !isPinned;
            await NOW_WINDOW.setAlwaysOnTop(nextPinned);
            isPinned = nextPinned;
        } catch (err) {
            console.error("창 최상단 고정 설정 실패:", err);
        }
    }
</script>

<button
    type="button"
    class="pin-button"
    class:pinned={isPinned}
    onclick={togglePin}
    aria-label={isPinned ? "화면 최상단 고정 해제" : "화면 최상단 고정"}
    title={isPinned ? "화면 최상단 고정 해제" : "화면 최상단 고정"}
>
    {#if isPinned}
        <!-- 고정 -->
        <svg
            class="icon pinned-icon"
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="currentColor"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <line x1="12" y1="17" x2="12" y2="22" />
            <path
                d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"
            />
        </svg>
    {:else}
        <!-- 미고정 -->
        <svg
            class="icon unpinned-icon"
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <line x1="12" y1="17" x2="12" y2="22" />
            <path
                d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"
            />
        </svg>
    {/if}
</button>

<style>
    button {
        border-radius: 50%;
        width: 20px;
        height: 20px;
        margin: 5px;
        flex-shrink: 0;
        box-sizing: border-box;

        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        border: none;
        outline: none;
        cursor: pointer;

        background-color: var(--bg);
        color: var(--fg);

        -webkit-app-region: no-drag;

        transition:
            background-color 0.2s ease,
            color 0.2s ease,
            border-color 0.2s ease,
            transform 0.1s ease;

        &:hover {
            background-color: var(--bg-hover);
            color: var(--fg-hover);
        }

        &:active {
            transform: scale(0.92);
        }

        &.pinned {
            background-color: var(--bg-accent);
            color: var(--fg-accent);

            &:hover {
                background-color: var(--bg-accent-hover);
                color: var(--fg-accent-hover);
            }
        }
    }

    svg {
        display: block;
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
</style>
