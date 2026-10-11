<script>
    let { children } = $props();
</script>

<div class="spacer">
    {@render children?.()}
</div>

<style>
    .spacer {
        /* 
           1. flex: 1 1 0px (flex-grow: 1, flex-shrink: 1)
              - 남는 여백 공간을 최대로 차지하도록 확장됩니다.
              - 공간이 부족해지면 유연하게 축소됩니다.
        */
        flex: 1 1 0px;

        /* 
           2. min-width: 0 (가장 중요!)
              - flex 아이템의 기본 min-width는 auto라서 내부 콘텐츠가 있을 때
                부모 컨테이너 크기보다 작아지지 못하고 밖으로 튀어나가는(overflow) 현상이 발생합니다.
              - min-width: 0을 주어야 부모 영역을 절대 벗어나지 않고 안전하게 줄어듭니다.
        */
        min-width: 0;
        min-height: 0;

        /* 내용물이 넘칠 경우 잘라내어 부모 밖으로 나가지 않도록 보호 */
        overflow: hidden;
    }
</style>
