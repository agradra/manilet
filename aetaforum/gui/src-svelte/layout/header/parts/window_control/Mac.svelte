<!-- Mac2.svelte — macOS 신호등 버튼 (Svelte 5)
  규칙:
  1. 호버는 그룹 단위 (하나에 올려도 세 버튼 아이콘 동시 표시)
  2. 아이콘: 빨강 ×, 노랑 −, 초록 +
  3. 비활성 창 → 전부 회색, 호버 시 복원
  4. 클릭 중 색상 어두워짐
-->
<script>
    import { getCurrentWindow } from "@tauri-apps/api/window";
    import { onMount } from "svelte";

    const NOW_WINDOW = getCurrentWindow();

    let isFocused = $state(true); // 창 포커스 여부

    onMount(() => {
        // 포커스 감지
        const handleFocus = () => (isFocused = true);
        const handleBlur = () => (isFocused = false);
        window.addEventListener("focus", handleFocus);
        window.addEventListener("blur", handleBlur);

        // cleanup
        return () => {
            window.removeEventListener("focus", handleFocus);
            window.removeEventListener("blur", handleBlur);
        };
    });
</script>

<div class="control_box" class:unfocused={!isFocused}>
    <!-- 닫기 -->
    <button
        class="close"
        aria-label="닫기"
        title="닫기"
        onclick={() => NOW_WINDOW.close()}
    >
        <svg
            width="7"
            height="7"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                stroke="currentColor"
                stroke-width="1.2"
                stroke-linecap="round"
                d="M1.182 5.99L5.99 1.182M5.99 6.132L1.182 1.323"
            />
        </svg>
    </button>

    <!-- 최소화 -->
    <button
        class="min"
        aria-label="최소화"
        title="최소화"
        onclick={() => NOW_WINDOW.minimize()}
    >
        <svg
            width="7"
            height="2"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                stroke="currentColor"
                stroke-width="1.2"
                stroke-linecap="round"
                d="M.61.703h5.8"
            />
        </svg>
    </button>

    <!-- 최대화 -->
    <button
        class="max"
        aria-label="최대화"
        title="최대화"
        onclick={() => NOW_WINDOW.toggleMaximize()}
    >
        <svg
            width="8"
            height="7"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                stroke="currentColor"
                stroke-width="1.2"
                stroke-linecap="round"
                d="M1.1 3.4h5.8M3.9 6.4V.6"
            />
        </svg>
    </button>
</div>

<style>
    /* =========================================
       색상 변수
    ========================================= */
    .control_box {
        /* 버튼 전역 */
        --size: 14px;
        --gap: 9px;
        --border-width: 0.5px;
        --icon-color: #0000007e;

        /* 비활성화 */
        --disable: #444444;
        --disable-border: #4c4c4c;

        /* 닫기 */
        --close-bg: #ff5c60;
        --close-border: #ff3335;

        /* 최소화 */
        --min-bg: #fac800;
        --min-border: #f8af00;

        /* 최대화 */
        --max-bg: #35c759;
        --max-border: #1dae31;

        display: flex;
        align-items: center;
        height: 100%;
        padding: 8px;
        gap: var(--gap);
        flex-shrink: 0;
        box-sizing: border-box;
        -webkit-app-region: no-drag;
    }

    button {
        width: var(--size);
        height: var(--size);
        border-radius: 50%;
        border: none;
        padding: 0;
        margin: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        position: relative;
        box-sizing: border-box;
        transition:
            background-color 0.2s ease-in-out,
            box-shadow 0.2s ease-in-out,
            filter 0.15s ease-out;

        svg {
            color: var(--icon-color);
        }
    }

    button.close {
        background-color: var(--close-bg);
        box-shadow: inset 0 0 0 var(--border-width) var(--close-border);
    }
    button.min {
        background-color: var(--min-bg);
        box-shadow: inset 0 0 0 var(--border-width) var(--min-border);
    }
    button.max {
        background-color: var(--max-bg);
        box-shadow: inset 0 0 0 var(--border-width) var(--max-border);
    }

    /* 아이콘 */
    svg {
        display: block;
        opacity: 0;
        pointer-events: none;
        user-select: none;
        transition: opacity 0.2s ease-in-out;
    }

    /* 비활성 창 */
    .unfocused button {
        background-color: var(--disable);
        box-shadow: inset 0 0 0 var(--border-width) var(--disable-border);
    }
    /* 버튼 하나에 올려도 세 아이콘 동시 표시 */
    .control_box:has(button:hover) svg {
        opacity: 1;
    }

    /* 눌림 — 색상 어두워짐 */
    button:active {
        filter: brightness(0.8);
    }

    /* 비활성 창이어도 호버하면 색과 아이콘 복원 */
    .control_box.unfocused:has(button:hover) button.close {
        background-color: var(--close-bg);
        box-shadow: inset 0 0 0 0.5px var(--close-border);
    }
    .control_box.unfocused:has(button:hover) button.min {
        background-color: var(--min-bg);
        box-shadow: inset 0 0 0 0.5px var(--min-border);
    }
    .control_box.unfocused:has(button:hover) button.max {
        background-color: var(--max-bg);
        box-shadow: inset 0 0 0 0.5px var(--max-border);
    }
</style>
