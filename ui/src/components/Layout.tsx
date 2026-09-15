import type { ReactNode } from "react";
import { NavLink, Link } from "react-router-dom";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="app-header">
        <div className="bar">
          <Link to="/" className="brand">ARGUS</Link>
          <nav className="app-nav">
            <NavLink to="/" end>New Run</NavLink>
            <NavLink to="/runs">History</NavLink>
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
    </>
  );
}
