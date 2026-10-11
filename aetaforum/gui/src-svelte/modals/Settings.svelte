<script>
    import { onMount } from "svelte";
    import { getCurrentWindow } from "@tauri-apps/api/window";
    import { settingsStore, initSettings, saveSettings } from "../lib/settings.js";

    const appWindow = getCurrentWindow();

    // 현재 선택된 메뉴 탭
    let activeTab = "theme";

    let windowControlStyle = "system";
    let theme = "dark";
    let language = "ko";

    onMount(async () => {
        await initSettings();
        if ($settingsStore) {
            windowControlStyle = $settingsStore.window_control_style || "system";
        }
    });

    $: if ($settingsStore && $settingsStore.window_control_style) {
        windowControlStyle = $settingsStore.window_control_style;
    }

    function closeSettings() {
        appWindow.close();
    }

    async function handleStyleChange(newStyle) {
        windowControlStyle = newStyle;
        try {
            await saveSettings({
                window_control_style: windowControlStyle,
            });
        } catch (e) {
            console.error("설정 저장 실패:", e);
        }
    }

    async function confirmSettings() {
        try {
            await saveSettings({
                window_control_style: windowControlStyle,
            });
        } catch (e) {
            console.error("설정 저장 실패:", e);
        }
        closeSettings();
    }
</script>

<div class="settings-container">
    <!-- 좌측 메뉴 네비게이션 -->
    <aside class="sidebar">
        <h2 class="title">Settings</h2>
        <nav class="menu">
            <button
                class:active={activeTab === "theme"}
                on:click={() => (activeTab = "theme")}
            >
                테마 및 디자인
            </button>
            <button
                class:active={activeTab === "version"}
                on:click={() => (activeTab = "version")}
            >
                버전 정보
            </button>
            <button
                class:active={activeTab === "log"}
                on:click={() => (activeTab = "log")}
            >
                로그 (Log)
            </button>
            <button
                class:active={activeTab === "language"}
                on:click={() => (activeTab = "language")}
            >
                언어 (Language)
            </button>
        </nav>
    </aside>

    <!-- 우측 메인 컨텐츠 영역 -->
    <main class="content-area">
        <div class="content">
            {#if activeTab === "theme"}
                <h3>테마 및 디자인 설정</h3>

                <!-- 창 조절 버튼 스타일 설정 -->
                <div class="panel">
                    <h4>상단바 창 조절 버튼 스타일</h4>
                    <p class="desc">
                        창 제어 버튼(최소화, 최대화, 닫기)의 시각 디자인을 선택합니다.
                    </p>

                    <div class="style-options">
                        <!-- 시스템 기본 -->
                        <label
                            class="style-card"
                            class:selected={windowControlStyle === "system"}
                        >
                            <input
                                type="radio"
                                name="controlStyle"
                                value="system"
                                checked={windowControlStyle === "system"}
                                on:change={() => handleStyleChange("system")}
                            />
                            <div class="card-content">
                                <div class="card-header-row">
                                    <span class="card-title">시스템 기본 (System)</span>
                                    <span class="badge">기본값</span>
                                </div>
                                <span class="card-desc">
                                    현재 OS 환경을 자동 감지합니다. (Mac: Mac 스타일, Windows/Linux: 윈도우 스타일)
                                </span>
                            </div>
                        </label>

                        <!-- Mac 스타일 -->
                        <label
                            class="style-card"
                            class:selected={windowControlStyle === "mac"}
                        >
                            <input
                                type="radio"
                                name="controlStyle"
                                value="mac"
                                checked={windowControlStyle === "mac"}
                                on:change={() => handleStyleChange("mac")}
                            />
                            <div class="card-content">
                                <div class="card-header-row">
                                    <span class="card-title">Mac 스타일</span>
                                    <span class="preview-mac">
                                        <span class="dot red"></span>
                                        <span class="dot yellow"></span>
                                        <span class="dot green"></span>
                                    </span>
                                </div>
                                <span class="card-desc">
                                    애플 macOS 트래픽 라이트 원형 버튼 디자인 (상단바 좌측 배치)
                                </span>
                            </div>
                        </label>

                        <!-- Windows 스타일 -->
                        <label
                            class="style-card"
                            class:selected={windowControlStyle === "windows"}
                        >
                            <input
                                type="radio"
                                name="controlStyle"
                                value="windows"
                                checked={windowControlStyle === "windows"}
                                on:change={() => handleStyleChange("windows")}
                            />
                            <div class="card-content">
                                <div class="card-header-row">
                                    <span class="card-title">Windows 스타일</span>
                                    <span class="preview-win">
                                        <span>−</span>
                                        <span>□</span>
                                        <span>✕</span>
                                    </span>
                                </div>
                                <span class="card-desc">
                                    마이크로소프트 윈도우 직사각형 컨트롤 디자인 (상단바 우측 배치)
                                </span>
                            </div>
                        </label>
                    </div>
                </div>

                <!-- 테마 모드 -->
                <div class="panel" style="margin-top: 16px;">
                    <h4>색상 테마</h4>
                    <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; cursor: pointer;">
                        <input type="radio" name="theme" checked={theme === "dark"} />
                        <span>다크 모드 (Dark Theme)</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="radio" name="theme" checked={theme === "light"} disabled />
                        <span style="opacity: 0.6;">라이트 모드 (준비 중)</span>
                    </label>
                </div>
            {:else if activeTab === "version"}
                <h3>버전 정보</h3>
                <div class="panel">
                    <p><strong>Aetaforum</strong> v1.0.0</p>
                    <p class="desc">백테스팅 데이터 관리 및 결과 분석 플랫폼</p>
                </div>
            {:else if activeTab === "log"}
                <h3>시스템 로그</h3>
                <div class="panel code-panel">
                    <code>
                        [INFO] 시스템 초기화 완료<br />
                        [INFO] 설정 저장소: AppData/manilet/aetaforum/setting.json<br />
                        [INFO] 데이터베이스 연결 성공
                    </code>
                </div>
            {:else if activeTab === "language"}
                <h3>언어 설정</h3>
                <div class="panel">
                    <select>
                        <option value="ko">한국어 (Korean)</option>
                        <option value="en">English (US)</option>
                    </select>
                </div>
            {/if}
        </div>

        <!-- 하단 액션 버튼 -->
        <footer class="actions">
            <button class="btn-cancel" on:click={closeSettings}>취소</button>
            <button class="btn-confirm" on:click={confirmSettings}>확인</button>
        </footer>
    </main>
</div>

<style>
    .settings-container {
        display: flex;
        width: 100%;
        height: calc(100vh - 32px);
        box-sizing: border-box;
        background: var(--bg-surface, var(--bg, #1e1e24));
        color: var(--text-primary, #f8fafc);
        font-family: var(--sans, sans-serif);
    }

    /* 좌측 사이드바 */
    .sidebar {
        width: 220px;
        background: var(--bg-panel, rgba(19, 23, 34, 0.6));
        border-right: 1px solid var(--border-base, rgba(255, 255, 255, 0.08));
        padding: 20px 0;
        display: flex;
        flex-direction: column;
    }

    .title {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 20px;
        padding: 0 20px;
        color: var(--text-primary, #fff);
    }

    .menu {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .menu button {
        background: transparent;
        border: none;
        color: var(--text-secondary, #94a3b8);
        padding: 12px 20px;
        text-align: left;
        font-family: inherit;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.15s;
    }

    .menu button:hover {
        background: var(--bg-panel-hover, rgba(255, 255, 255, 0.05));
        color: var(--text-primary, #fff);
    }

    .menu button.active {
        background: var(--accent-transparent, rgba(59, 130, 246, 0.15));
        color: var(--accent-primary, #3b82f6);
        border-right: 3px solid var(--accent-primary, #3b82f6);
        font-weight: 600;
    }

    /* 우측 콘텐츠 영역 */
    .content-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 28px;
        overflow-y: auto;
    }

    .content {
        flex: 1;
    }

    h3 {
        margin-top: 0;
        color: var(--text-primary, #fff);
        font-size: 1.4rem;
        margin-bottom: 20px;
    }

    h4 {
        margin: 0 0 6px 0;
        font-size: 1.05rem;
        color: var(--text-primary, #fff);
    }

    .panel {
        background: var(--bg-panel, rgba(19, 23, 34, 0.5));
        border: 1px solid var(--border-base, rgba(255, 255, 255, 0.08));
        border-radius: 8px;
        padding: 20px;
    }

    .desc {
        color: var(--text-secondary, #94a3b8);
        font-size: 0.88rem;
        margin-top: 0;
        margin-bottom: 16px;
    }

    /* 스타일 선택 카드 */
    .style-options {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .style-card {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 14px 16px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--border-base, rgba(255, 255, 255, 0.08));
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .style-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.2);
    }

    .style-card.selected {
        background: var(--accent-transparent, rgba(59, 130, 246, 0.12));
        border-color: var(--accent-primary, #3b82f6);
    }

    .style-card input[type="radio"] {
        margin-top: 4px;
        cursor: pointer;
        accent-color: var(--accent-primary, #3b82f6);
    }

    .card-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .card-header-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .card-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: var(--text-primary, #fff);
    }

    .card-desc {
        font-size: 0.83rem;
        color: var(--text-secondary, #94a3b8);
        line-height: 1.4;
    }

    .badge {
        font-size: 0.72rem;
        padding: 2px 6px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
        color: var(--text-secondary, #94a3b8);
    }

    /* 프리뷰 뱃지 */
    .preview-mac {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 8px;
        border-radius: 12px;
        background: rgba(0, 0, 0, 0.3);
    }

    .dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
    }

    .dot.red { background-color: #ff5f56; }
    .dot.yellow { background-color: #ffbd2e; }
    .dot.green { background-color: #27c93f; }

    .preview-win {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(0, 0, 0, 0.3);
        font-size: 10px;
        color: #bbb;
    }

    .code-panel {
        background: var(--code-bg, #11131a);
        font-family: var(--mono, monospace);
        font-size: 0.85rem;
        color: #a6accd;
    }

    /* 하단 확인/닫기 버튼 */
    .actions {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--border-base, rgba(255, 255, 255, 0.08));
    }

    .actions button {
        padding: 8px 24px;
        border-radius: 6px;
        border: none;
        font-family: inherit;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn-cancel {
        background: transparent;
        border: 1px solid var(--border-base, rgba(255, 255, 255, 0.2));
        color: var(--text-secondary, #94a3b8);
    }

    .btn-cancel:hover {
        background: rgba(255, 255, 255, 0.08);
        color: var(--text-primary, #fff);
    }

    .btn-confirm {
        background: var(--accent-primary, #3b82f6);
        color: #fff;
    }

    .btn-confirm:hover {
        opacity: 0.9;
        box-shadow: 0 0 12px var(--accent-transparent, rgba(59, 130, 246, 0.4));
    }
</style>
