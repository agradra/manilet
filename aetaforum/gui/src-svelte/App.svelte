<script>
    import { invoke } from '@tauri-apps/api/core';

    let query = 'BTC';
    let results = null;
    let loading = false;
    let error = null;

    function minimize() { invoke('minimize_window'); }
    function toggleMaximize() { invoke('toggle_maximize_window'); }
    function closeWindow() { invoke('close_window'); }

    async function search() {
        loading = true;
        error = null;
        try {
            results = await invoke('search_futures', { query, maxSymbols: 12 });
        } catch (e) {
            error = e.toString();
        } finally {
            loading = false;
        }
    }
</script>

<div class="titlebar" data-tauri-drag-region>
    <div class="drag-area" data-tauri-drag-region>
        <span class="title">Aetaforum</span>
    </div>
    <div class="window-controls">
        <button class="control-btn minimize" on:click={minimize}>−</button>
        <button class="control-btn maximize" on:click={toggleMaximize}>□</button>
        <button class="control-btn close" on:click={closeWindow}>✕</button>
    </div>
</div>

<main>
    <div class="content" data-tauri-drag-region>
        <h2>Futures Scanner (100% Rust)</h2>
        <div class="search-bar">
            <input type="text" bind:value={query} on:keydown={e => e.key === 'Enter' && search()} placeholder="Enter symbol (e.g. BTC)" />
            <button on:click={search} disabled={loading}>
                {loading ? 'Searching...' : 'Search'}
            </button>
        </div>

        {#if error}
            <div class="error">Error: {error}</div>
        {/if}

        {#if results}
            <div class="results">
                <p>Found {results.summary.total} symbols ({results.summary.trading} trading).</p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Exchange</th>
                                <th>Market</th>
                                <th>Symbol</th>
                                <th>Status</th>
                                <th>First Candle</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each ['binance', 'bybit', 'hyperliquid'] as ex}
                                {#if results.results[ex]}
                                    {#each results.results[ex] as sym}
                                        <tr>
                                            <td>{sym.exchange}</td>
                                            <td>{sym.market}</td>
                                            <td><strong>{sym.symbol}</strong></td>
                                            <td>{sym.is_trading ? '🟢 Trading' : '🔴 Closed'}</td>
                                            <td>{sym.first_candle_time ? sym.first_candle_time.substring(0, 10) : '-'}</td>
                                        </tr>
                                    {/each}
                                {/if}
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        {/if}
    </div>
</main>

<style>
  /* 커스텀 타이틀 바 스타일 (인텔리제이 / VS Code 느낌) */
  .titlebar {
      display: flex;
      height: 32px;
      background-color: #252526; /* 상단바 색상 */
      user-select: none;
      width: 100%;
      border-bottom: 1px solid #333;
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
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      font-size: 12px;
  }
  
  .control-btn:hover {
      background-color: rgba(255, 255, 255, 0.1);
  }
  
  .control-btn.close:hover {
      background-color: #e81123;
      color: white;
  }
  
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

  th, td {
      padding: 10px;
      border-bottom: 1px solid #333;
  }

  th {
      background: rgba(255, 255, 255, 0.05);
      position: sticky;
      top: 0;
  }
</style>
