export type VIEW_MODE = 'lab' | 'archive' | 'data';

class ViewManager {
    now_view_mode = $state<VIEW_MODE>('lab');

    setView(view: VIEW_MODE) {
        this.now_view_mode = view;
    }
}

export const viewManager = new ViewManager();