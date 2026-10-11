<script>
    import { onMount } from "svelte";
    import { viewManager } from "../../../lib/view_state.svelte";

    // src-svelte/assets 디렉토리의 모든 SVG 파일을 raw 문자열로 가져오기
    const svgModules = import.meta.glob("../../../assets/*.svg", {
        query: "?raw",
        import: "default",
        eager: true,
    });

    // 파일명 기반 svg 매핑 맵 생성 (예: 'lab', 'lab-active', 'archive', etc.)
    const svgMap = {};
    for (const [path, content] of Object.entries(svgModules)) {
        const filename = path.split("/").pop();
        if (filename && filename.endsWith(".svg")) {
            const name = filename.slice(0, -4);
            svgMap[name] = content;
        }
    }

    // 기본 제공 뷰 모드 아이템 목록
    const DEFAULT_ITEMS = [
        { id: "lab", label: "Lab" },
        { id: "archive", label: "Archive" },
        { id: "data", label: "Data" },
    ];

    let { items = DEFAULT_ITEMS, onchange } = $props();

    let buttonRefs = $state({});
    let isReady = $state(false);

    // viewManager.now_view_mode에 따른 현재 활성화 인덱스
    let activeIndex = $derived.by(() => {
        const idx = items.findIndex(
            (item) => item.id === viewManager.now_view_mode,
        );
        return idx >= 0 ? idx : 0;
    });

    // 이름 및 활성화 여부로 SVG 가져오기 (오타 등으로 못 찾으면 null 반환)
    function getSvg(name, isActive) {
        const key = isActive ? `${name}-active` : name;
        return svgMap[key] || null;
    }

    // 버튼 선택 시 viewManager 변경
    function selectItem(id) {
        if (viewManager.now_view_mode === id) return;
        viewManager.setView(id);
        onchange?.(id);
    }

    // Ctrl + 1, 2, 3... 단축키 지원
    function handleKeyCombination(event) {
        if (
            (event.ctrlKey || event.metaKey) &&
            !event.shiftKey &&
            !event.altKey
        ) {
            const digit = parseInt(event.key, 10);
            if (!isNaN(digit) && digit >= 1 && digit <= items.length) {
                event.preventDefault();
                const targetItem = items[digit - 1];
                if (targetItem) {
                    selectItem(targetItem.id);
                }
            }
        }
    }

    onMount(() => {
        // 첫 렌더링 후 애니메이션 활성화 (초기 깜빡임 방지)
        requestAnimationFrame(() => {
            isReady = true;
        });
    });
</script>

<svelte:window onkeydown={handleKeyCombination} />

<div class="button-bar" role="tablist">
    <!-- 인디케이터 -->
    <div
        class="indicator"
        class:animated={isReady}
        style="transform: translateX(calc({activeIndex} * (var(--btn-size) + var(--bar-gap))));"
        aria-hidden="true"
    ></div>

    {#each items as item, index (item.id)}
        {@const isSelected = item.id === viewManager.now_view_mode}
        {@const svgContent = getSvg(item.id, isSelected)}

        <button
            type="button"
            class="bar-item"
            class:active={isSelected}
            bind:this={buttonRefs[item.id]}
            onclick={() => selectItem(item.id)}
            role="tab"
            aria-selected={isSelected}
            tabindex={isSelected ? 0 : -1}
            title="{item.label || item.id} (Ctrl+{index + 1})"
            aria-label="{item.label || item.id} (Ctrl+{index + 1})"
        >
            <span class="icon-wrapper">
                {#if svgContent}
                    {@html svgContent}
                {/if}
            </span>
        </button>
    {/each}
</div>

<style>
    .button-bar {
        --btn-size: 32px;
        --bar-pad: 4px;
        --bar-gap: 4px;
        --icon-size: 18px;

        position: relative;
        display: inline-flex;
        align-items: center;
        padding: var(--bar-pad);
        gap: var(--bar-gap);
        height: calc(var(--btn-size) + var(--bar-pad) * 2);
        background-color: var(--bg);
        border-radius: 9999px;
        box-sizing: border-box;
        user-select: none;
        -webkit-app-region: no-drag;
    }

    .indicator {
        /* 인디케이터 */
        position: absolute;
        top: var(--bar-pad);
        left: var(--bar-pad);
        width: var(--btn-size);
        height: var(--btn-size);
        border-radius: 50%;
        background-color: var(--bg-accent);
        pointer-events: none;
        z-index: 0;
        will-change: transform;
    }

    .indicator.animated {
        transition: transform 0.28s cubic-bezier(0.25, 1, 0.5, 1);
    }

    /* 원형 버튼 아이템 */
    .bar-item {
        position: relative;
        z-index: 1;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: var(--btn-size);
        height: var(--btn-size);
        border-radius: 50%;
        border: none;
        outline: none;
        background: transparent;
        cursor: pointer;
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        color: var(--fg-disable);
        -webkit-tap-highlight-color: transparent;
        transition:
            color 0.2s ease,
            transform 0.12s ease;

        &:hover:not(.active) {
            color: var(--fg-hover, #ffffff);
            background-color: rgba(255, 255, 255, 0.06);
        }

        &:active:not(.active) {
            transform: scale(0.92);
        }

        /* 활성화 시 아이콘 색상 반전 (하얀 배경 위에서 선명하게 표시) */
        &.active {
            color: var(--fg-accent, #121212);
        }

        &:focus-visible {
            outline: 2px solid var(--accent-primary, #3b82f6);
            outline-offset: 1px;
        }
    }

    /* 아이콘 래퍼 */
    .icon-wrapper {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: var(--icon-size);
        height: var(--icon-size);
        flex-shrink: 0;
        transition: transform 0.22s cubic-bezier(0.34, 1.4, 0.64, 1);
    }

    .icon-wrapper :global(svg) {
        width: 100%;
        height: 100%;
        display: block;
    }

    /* 활성화 시 아이콘 살짝 확대 팝 */
    .bar-item.active .icon-wrapper {
        transform: scale(1.08);
    }
</style>
