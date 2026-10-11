<!-- Windows.svelte — Windows 창 컨트롤 버튼 (Svelte 5)
  규칙:
  1. 버튼 순서: 최소화(−), 최대화/복원(□/❐), 닫기(✕)
  2. 창 최대화 여부에 따라 최대화(□) / 복원(❐) 아이콘 동적 전환
  3. 비활성 창 → 아이콘 흐려짐(dimmed), 호버 시 선명하게 복원
  4. 호버 효과:
     - 최소화/최대화: 부드러운 반투명 밝은 배경
     - 닫기: Windows 시그니처 레드(#e81123) 및 흰색 아이콘
  5. 클릭 중(active): 살짝 더 어두운 배경/레드
-->
<script>
    import { getCurrentWindow } from "@tauri-apps/api/window";
    import { onMount } from "svelte";

    const NOW_WINDOW = getCurrentWindow();

    let isFocused = $state(true); // 창 포커스 여부
    let isMaximized = $state(false); // 창 최대화 여부

    onMount(() => {
        // 포커스 감지
        const handleFocus = () => (isFocused = true);
        const handleBlur = () => (isFocused = false);
        window.addEventListener("focus", handleFocus);
        window.addEventListener("blur", handleBlur);

        // 최대화 상태 초기화 및 감지
        const updateMaximized = async () => {
            try {
                isMaximized = await NOW_WINDOW.isMaximized();
            } catch (e) {
                // 웹 브라우저 환경 등 예외 처리
            }
        };

        updateMaximized();
        window.addEventListener("resize", updateMaximized);

        // cleanup
        return () => {
            window.removeEventListener("focus", handleFocus);
            window.removeEventListener("blur", handleBlur);
            window.removeEventListener("resize", updateMaximized);
        };
    });

    async function toggleMaximize() {
        try {
            await NOW_WINDOW.toggleMaximize();
            isMaximized = await NOW_WINDOW.isMaximized();
        } catch (e) {
            console.error("toggleMaximize error:", e);
        }
    }
</script>

<div class="control_box" class:unfocused={!isFocused}>
    <!-- 최소화 -->
    <button
        class="min"
        aria-label="최소화"
        title="최소화"
        onclick={() => NOW_WINDOW.minimize()}
    >
        <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path stroke="currentColor" stroke-width="1" d="M0 5h10" />
        </svg>
    </button>

    <!-- 최대화 / 복원 -->
    <button
        class="max"
        aria-label={isMaximized ? "복원" : "최대화"}
        title={isMaximized ? "복원" : "최대화"}
        onclick={toggleMaximize}
    >
        {#if isMaximized}
            <!-- 복원 -->
            <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
            >
                <path stroke="currentColor" stroke-width="1" d="M2.5 .5h7v7" />
                <rect
                    x="0.5"
                    y="2.5"
                    width="7"
                    height="7"
                    stroke="currentColor"
                    stroke-width="1"
                />
            </svg>
        {:else}
            <!-- 최대화 -->
            <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
            >
                <rect
                    x="0.5"
                    y="0.5"
                    width="9"
                    height="9"
                    stroke="currentColor"
                    stroke-width="1"
                />
            </svg>
        {/if}
    </button>

    <!-- 닫기 -->
    <button
        class="close"
        aria-label="닫기"
        title="닫기"
        onclick={() => NOW_WINDOW.close()}
    >
        <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                stroke="currentColor"
                stroke-width="1"
                d="M.5.5l9 9M9.5.5l-9 9"
            />
        </svg>
    </button>
</div>

<style>
    .control_box {
        /* 버튼 크기 */
        --btn-width: 46px;
        --btn-height: 100%;

        /* 아이콘 */
        --icon-color: #cccccc;
        --icon-hover: #ffffff;
        --icon-unfocused: #777777;

        /* 호버 / 클릭 배경 */
        --hover-bg: rgba(255, 255, 255, 0.08);
        --active-bg: rgba(255, 255, 255, 0.15);

        /* 닫기 버튼 전용 색상 */
        --close-hover-bg: #e81123;
        --close-active-bg: #c4101e;
        --close-hover-color: #ffffff;

        display: flex;
        align-items: center;
        height: 100%;
        -webkit-app-region: no-drag;
    }

    /* 라이트 모드 지원 */
    :global(:root[data-theme="light"]) .control_box {
        --icon-color: #18181b;
        --icon-hover: #000000;
        --icon-unfocused: #8a8a8e;

        --hover-bg: rgba(0, 0, 0, 0.06);
        --active-bg: rgba(0, 0, 0, 0.12);
    }

    button {
        width: var(--btn-width);
        height: var(--btn-height);
        min-height: 32px;
        border: none;
        padding: 0;
        margin: 0;
        background: transparent;
        color: var(--icon-color);
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        outline: none;
        box-sizing: border-box;
        transition:
            background-color 0.15s ease,
            color 0.15s ease;
    }

    /* 일반 버튼 호버 및 클릭 */
    button:hover {
        background-color: var(--hover-bg);
        color: var(--icon-hover);
    }
    button:active {
        background-color: var(--active-bg);
    }

    /* 닫기 버튼 호버 및 클릭 (Windows 시그니처 레드) */
    button.close:hover {
        background-color: var(--close-hover-bg);
        color: var(--close-hover-color);
    }
    button.close:active {
        background-color: var(--close-active-bg);
        color: var(--close-hover-color);
    }

    /* 아이콘 */
    svg {
        display: block;
        pointer-events: none;
        user-select: none;
    }

    /* 비활성 창 */
    .unfocused button {
        color: var(--icon-unfocused);
    }

    /* 비활성 창이어도 마우스 올리면 선명하게 복원 */
    .unfocused button:hover {
        background-color: var(--hover-bg);
        color: var(--icon-hover);
    }
    .unfocused button.close:hover {
        background-color: var(--close-hover-bg);
        color: var(--close-hover-color);
    }
</style>
