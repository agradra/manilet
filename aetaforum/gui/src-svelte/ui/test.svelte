<script>
    // 1. 껍데기 div의 실제 너비와 높이를 실시간으로 담을 변수
    let w = 300;
    let h = 300;

    export let r = 10; // 모서리 둥글기 (절대 찌그러지지 않음!)
    export let cutW = 100; // 우측 상단 파인 부분의 너비
    export let cutH = 50; // 우측 상단 파인 부분의 높이

    // 💡 2. Svelte의 마법 ($:): w나 h가 1px라도 변하면 패스를 즉시 다시 계산합니다.
    // ⚠️ CSS clip-path: path()는 줄바꿈을 허용하지 않으므로 반드시 한 줄 문자열이어야 합니다.
    $: shapePath = [
        `M ${r} 0`,
        `L ${w - cutW - r} 0`,
        `A ${r} ${r} 0 0 1 ${w - cutW} ${r}`,
        `L ${w - cutW} ${cutH - r}`,
        `A ${r} ${r} 0 0 0 ${w - cutW + r} ${cutH}`,
        `L ${w - r} ${cutH}`,
        `A ${r} ${r} 0 0 1 ${w} ${cutH + r}`,
        `L ${w} ${h - r}`,
        `A ${r} ${r} 0 0 1 ${w - r} ${h}`,
        `L ${r} ${h}`,
        `A ${r} ${r} 0 0 1 0 ${h - r}`,
        `L 0 ${r}`,
        `A ${r} ${r} 0 0 1 ${r} 0`,
        `Z`
    ].join(' ');
</script>

<!-- 3. bind:clientWidth/Height 로 이 div의 실제 픽셀 크기를 w, h 변수에 묶어버립니다 -->
<div class="shape-wrapper" bind:clientWidth={w} bind:clientHeight={h}>
    <!-- 배경 유리 (동적 패스로 잘라냄) -->
    <div class="glass-background" style="clip-path: path('{shapePath}')">
        <slot />
        <!-- 내용물이 길어지면 h가 커지고, h가 커지면 패스가 다시 그려짐 -->
    </div>

    <!-- 테두리 덮어쓰기 (뷰박스도 실시간 w, h 적용) -->
    <!-- preserveAspectRatio="none"를 빼버리고 정확한 좌표에 그립니다 -->
    <svg class="border-overlay" viewBox="0 0 {w} {h}" width={w} height={h}>
        <path
            d={shapePath}
            fill="none"
            stroke="rgba(255, 255, 255, 0.2)"
            stroke-width="2"
        />
    </svg>
</div>

<style>
    .shape-wrapper {
        position: relative;
        width: 100%; /* 부모에 맞춰 마음껏 늘어나도 됩니다 */
        min-height: 150px;
        filter: drop-shadow(0px 10px 15px rgba(0, 13, 255, 0.5));
    }

    .glass-background {
        width: 100%;
        height: 100%;
        background-color: rgba(255, 0, 0, 0.5);
        backdrop-filter: blur(12px);
        padding: 20px; /* 내부 컨텐츠 여백 */
    }

    .border-overlay {
        position: absolute;
        top: 0;
        left: 0;
        pointer-events: none;
    }
</style>
