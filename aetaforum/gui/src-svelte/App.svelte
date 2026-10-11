<script>
    import { invoke } from "@tauri-apps/api/core";
    import Test from "./ui/test.svelte";
    import Header from "./layout/header/Header.svelte";
    import SubHeader from "./layout/header/SubHeader.svelte";
    import Settings from "./modals/Settings.svelte";
    import Mac2 from "./layout/header/parts/window_control/Mac.svelte";

    import Windows from "./layout/header/parts/window_control/Windows.svelte";

    let query = "BTC";
    let results = null;
    let loading = false;
    let error = null;

    import { getCurrentWindow } from "@tauri-apps/api/window";
    import Footer from "./layout/footer/Footer.svelte";
    const isSettingsWindow = getCurrentWindow().label === "settings";

    async function search() {
        loading = true;
        error = null;
        try {
            results = await invoke("search_futures", { query, maxSymbols: 12 });
        } catch (e) {
            error = e.toString();
        } finally {
            loading = false;
        }
    }
</script>

<Header />

<Footer />

<style>
    main {
        height: calc(100vh - 32px);
        display: flex;
        flex-direction: column;
        color: #e0e0e0;
        padding: 20px;
        box-sizing: border-box;
        overflow-y: auto;
    }

    .content {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    h2 {
        margin: 0;
        color: #61dafb;
    }

    .search-bar {
        display: flex;
        gap: 8px;
    }

    input {
        flex: 1;
        padding: 10px;
        border-radius: 6px;
        border: 1px solid #444;
        background: rgba(0, 0, 0, 0.5);
        color: white;
        font-size: 16px;
    }

    button {
        padding: 10px 20px;
        border-radius: 6px;
        border: none;
        background: #007acc;
        color: white;
        font-size: 16px;
        cursor: pointer;
    }

    button:disabled {
        background: #444;
        cursor: not-allowed;
    }

    .error {
        color: #ff5555;
        padding: 10px;
        background: rgba(255, 0, 0, 0.1);
        border-radius: 4px;
    }

    .results {
        display: flex;
        flex-direction: column;
        gap: 10px;
        flex: 1;
        overflow: hidden;
    }

    .table-container {
        flex: 1;
        overflow-y: auto;
        border-radius: 8px;
        border: 1px solid #333;
        background: rgba(0, 0, 0, 0.4);
    }

    table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
    }

    th,
    td {
        padding: 10px;
        border-bottom: 1px solid #333;
    }

    th {
        background: rgba(255, 255, 255, 0.05);
        position: sticky;
        top: 0;
    }

    .modal-overlay {
        position: fixed;
        top: 32px; /* 헤더 아래부터 */
        left: 0;
        width: 100%;
        height: calc(100vh - 32px);
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(4px);
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .modal-window {
        width: 80%;
        height: 80%;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: var(--shadow);
    }
</style>
