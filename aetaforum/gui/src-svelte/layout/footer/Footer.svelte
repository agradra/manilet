<script>
    import ButtonBar from "./parts/ButtonBar.svelte";
</script>

<footer>
    <ButtonBar />
</footer>

<style>
    footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        display: flex;
        align-items: center;
        padding: 6px;
        box-sizing: border-box;
        background-color: transparent;
        z-index: 100;
        -webkit-app-region: no-drag;
    }
</style>
