import type { ReactNode } from "react";

type NavItem = {
  label: string;
  path: string;
};

type LayoutProps = {
  navItems: readonly NavItem[];
  activePath: string;
  onNavigate: (path: string) => void;
  children: ReactNode;
};

export function Layout({ navItems, activePath, onNavigate, children }: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">QB</span>
          <div>
            <h1>题库后台</h1>
            <p>Word 导入 · 审核 · 练习 · 检索</p>
          </div>
        </div>

        <nav className="nav-list" aria-label="主导航">
          {navItems.map((item) => {
            const active = activePath === item.path;
            return (
              <button
                key={item.path}
                type="button"
                className={`nav-item ${active ? "active" : ""}`}
                onClick={() => onNavigate(item.path)}
              >
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main-pane">
        <header className="topbar">
          <div>
            <p className="eyebrow">Exam Bank MVP</p>
            <h2>结构化题库工作台</h2>
          </div>
          <div className="topbar-chip">支持自动切题与人工审核</div>
        </header>

        <section className="content-card">{children}</section>
      </main>
    </div>
  );
}
